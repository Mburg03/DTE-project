# src/storage.py
import os, csv, re, json, zipfile, hashlib
from datetime import datetime
from typing import List, Dict

# -------------------------
# Directorios de salida
# -------------------------
def ensure_lot_dir(base_output_dir: str, date_from: str, date_to: str) -> str:
    """
    Crea (si no existe) la carpeta del lote según el rango de fechas.
    Ej: data/downloads/2025-08-01_2025-08-31
    """
    lot_name = f"{date_from}_{date_to}"
    lot_dir = os.path.join(base_output_dir, "downloads", lot_name)
    os.makedirs(lot_dir, exist_ok=True)
    return lot_dir

def build_message_folder_name(message) -> str:
    """
    Nombre de subcarpeta por mensaje: YYYYMMDD_<asunto_sanitizado_40>_<id8>
    """
    headers = {h["name"].lower(): h["value"] for h in message.get("payload", {}).get("headers", [])}
    subj = headers.get("subject", "(sin asunto)")
    ymd  = _yyyymmdd_from_internal_date(message.get("internalDate", 0))
    subj_clean = _sanitize(subj)[:40] or "sin_asunto"
    suf = str(message.get("id", ""))[-8:]
    return f"{ymd}_{subj_clean}_{suf}"

def ensure_message_dir(lot_dir: str, message) -> str:
    """
    Crea (si no existe) la subcarpeta para ese mensaje dentro del lote.
    """
    msg_folder = build_message_folder_name(message)
    msg_dir = os.path.join(lot_dir, msg_folder)
    os.makedirs(msg_dir, exist_ok=True)
    return msg_dir

# -------------------------
# Helpers de nombres
# -------------------------
def _sanitize(text: str) -> str:
    """
    Sanitiza para nombres de archivo: quita tildes, símbolos raros y espacios dobles.
    """
    if not text:
        return "desconocido"
    mapping = str.maketrans("áéíóúÁÉÍÓÚñÑ", "aeiouAEIOUnN")
    text = text.translate(mapping)
    text = re.sub(r"[^\w\s.-]+", "", text, flags=re.UNICODE)
    text = re.sub(r"\s+", "_", text).strip("_")
    return text or "desconocido"

def _extract_sender_name(from_header: str) -> str:
    """
    Intenta obtener un nombre corto del remitente (display name o parte antes de @).
    """
    if not from_header:
        return "remitente"
    m = re.search(r'^"?([^"<]+?)"?\s*<', from_header)
    if m:
        return _sanitize(m.group(1))
    m = re.search(r'([^@<\s]+)@', from_header)
    return _sanitize(m.group(1) if m else "remitente")

def _yyyymmdd_from_internal_date(internal_ms: int) -> str:
    """
    Convierte internalDate (ms epoch) a YYYYMMDD.
    """
    dt = datetime.utcfromtimestamp(int(internal_ms) / 1000.0)
    return dt.strftime("%Y%m%d")

def build_standard_filename(message, original_filename: str) -> str:
    """
    Construye un nombre estándar conservando la extensión original:
    YYYYMMDD_Proveedor_original.ext
    """
    headers = {h["name"].lower(): h["value"] for h in message.get("payload", {}).get("headers", [])}
    sender = _extract_sender_name(headers.get("from", ""))
    ymd = _yyyymmdd_from_internal_date(message.get("internalDate", 0))
    base = f"{ymd}_{sender}_{original_filename}"
    base = _sanitize(base)
    return base

# -------------------------
# Guardado y reporte
# -------------------------
def save_pdf_bytes(dir_path: str, filename: str, data: bytes) -> str:
    """
    Guarda bytes en disco (para .pdf o .json). Si el archivo existe, agrega sufijo incremental.
    """
    path = os.path.join(dir_path, filename)
    if os.path.exists(path):
        stem, ext = os.path.splitext(filename)
        i = 2
        while True:
            candidate = os.path.join(dir_path, f"{stem}({i}){ext}")
            if not os.path.exists(candidate):
                path = candidate
                break
            i += 1
    with open(path, "wb") as f:
        f.write(data)
    return path

def append_csv_report(dir_path: str, rows: List[Dict], filename: str = "reporte.csv") -> str:
    """
    Agrega filas al CSV del lote. Crea encabezados si no existe.
    Campos esperados en cada row:
      fecha, remitente, asunto, archivo_local, messageId, attachmentId
    """
    csv_path = os.path.join(dir_path, filename)
    file_exists = os.path.exists(csv_path)
    fieldnames = ["fecha", "remitente", "asunto", "archivo_local", "messageId", "attachmentId"]

    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for r in rows:
            writer.writerow(r)
    return csv_path

# -------------------------
# ZIP del lote (recursivo)
# -------------------------
def make_zip(lot_dir: str, zip_out_dir: str = None, zip_name: str = None) -> str:
    """
    Comprime PDFs/JSONs (y reporte.csv) del lote de forma recursiva, preservando subcarpetas.
    Devuelve la ruta del .zip.
    """
    base_dir = os.path.dirname(lot_dir)
    zip_out_dir = zip_out_dir or os.path.join(base_dir, "out")
    os.makedirs(zip_out_dir, exist_ok=True)

    lot_basename = os.path.basename(lot_dir)
    zip_name = zip_name or f"{lot_basename}.zip"
    zip_path = os.path.join(zip_out_dir, zip_name)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(lot_dir):
            for fname in files:
                low = fname.lower()
                if low.endswith((".pdf", ".json")) or fname == "reporte.csv":
                    full = os.path.join(root, fname)
                    arc  = os.path.relpath(full, lot_dir)  # conserva subcarpetas
                    zf.write(full, arcname=arc)
    return zip_path

# -------------------------
# Deduplicación por hash
# -------------------------
def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def load_hash_index(lot_dir: str) -> set:
    path = os.path.join(lot_dir, ".hashes.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                return set(json.load(f))
            except Exception:
                return set()
    return set()

def save_hash_index(lot_dir: str, hashes: set):
    path = os.path.join(lot_dir, ".hashes.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(sorted(list(hashes)), f, ensure_ascii=False)
