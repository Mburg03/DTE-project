# src/main.py
import argparse, os, yaml
from dotenv import load_dotenv
from logging_conf import setup_logging
from filters import build_gmail_query
from gmail_client import (
    get_gmail_service,
    search_messages,
    get_message,
    count_pdf_attachments,   # solo para loguear cuántos PDFs detecta
    download_attachments,    # usamos esta para PDF + JSON
)
from state import load_processed, append_processed
from storage import (
    ensure_lot_dir,
    ensure_message_dir,          # nuevo: subcarpeta por correo
    build_standard_filename,
    save_pdf_bytes,
    append_csv_report,
    make_zip,
    sha256_bytes,
    load_hash_index,
    save_hash_index,
)

def load_config():
    with open("config/config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def parse_args():
    ap = argparse.ArgumentParser(description="DTE Bot - descargar adjuntos (PDF/JSON), zipear y enviar (con dedupe y subcarpetas).")
    ap.add_argument("--from", dest="date_from", required=True, help="YYYY-MM-DD")
    ap.add_argument("--to", dest="date_to", required=True, help="YYYY-MM-DD")
    ap.add_argument("--download", action="store_true", help="Descargar y guardar adjuntos en disco")
    ap.add_argument("--zip", action="store_true", help="Crear ZIP del lote")
    ap.add_argument("--send", action="store_true", help="Enviar correo a la contadora con el ZIP")
    return ap.parse_args()

def main():
    load_dotenv()
    logger = setup_logging()
    cfg = load_config()
    args = parse_args()

    # Armar query Gmail
    query = build_gmail_query(cfg["keywords"], args.date_from, args.date_to, cfg.get("label"))
    logger.info(f"Query Gmail: {query}")

    gmail = get_gmail_service()
    ids = search_messages(gmail, query, max_results=cfg.get("max_results", 100))
    logger.info(f"Mensajes encontrados: {len(ids)}")

    lot_dir = None
    if args.download or args.zip or args.send:
        lot_dir = ensure_lot_dir(cfg.get("output_dir", "data"), args.date_from, args.date_to)
        logger.info(f"Carpeta de lote: {lot_dir}")

    # --- DEDUPE ---
    state_path = "data/state/processed.jsonl"
    seen = load_processed(state_path)
    lot_hashes = load_hash_index(lot_dir) if lot_dir else set()

    total_pdfs = 0
    csv_buffer = []
    processed_keys_to_append = []

    for i, mid in enumerate(ids, 1):
        msg = get_message(gmail, mid)

        pdfs = count_pdf_attachments(msg)
        total_pdfs += pdfs

        headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}
        subj = headers.get("subject", "(sin asunto)")
        frm  = headers.get("from", "(sin remitente)")
        logger.info(f"[{i:03d}] PDFs:{pdfs}  From:{frm}  Subject:{subj}")

        # Descargar PDF + JSON
        atts = download_attachments(gmail, msg, exts=("pdf","json"))
        logger.info(f"      -> Adjuntos listos: {len(atts)}")

        # Crear subcarpeta para este mensaje
        msg_dir = None
        if args.download and atts:
            msg_dir = ensure_message_dir(lot_dir, msg)

        if args.download and atts:
            for a in atts:
                unique_key = f"{mid}:{a['attachment_id']}"
                if unique_key in seen:
                    logger.info("         ↷ Omitido (ya procesado ese adjunto).")
                    continue

                h = sha256_bytes(a["data"])
                if h in lot_hashes:
                    logger.info("         ↷ Omitido (archivo idéntico ya guardado en este lote).")
                    processed_keys_to_append.append(unique_key)
                    continue

                std_name = build_standard_filename(msg, a["filename"])
                out_path = save_pdf_bytes(msg_dir or lot_dir, std_name, a["data"])
                logger.info(f"         ✓ Guardado: {out_path}")

                lot_hashes.add(h)
                csv_buffer.append({
                    "fecha": std_name[:8],  # YYYYMMDD
                    "remitente": frm,
                    "asunto": subj,
                    "archivo_local": out_path,
                    "messageId": mid,
                    "attachmentId": a["attachment_id"],
                })
                processed_keys_to_append.append(unique_key)

    # Guardar estado y hashes
    if processed_keys_to_append:
        append_processed(state_path, processed_keys_to_append)
    if lot_dir is not None:
        save_hash_index(lot_dir, lot_hashes)

    if args.download and csv_buffer:
        csv_path = append_csv_report(lot_dir, csv_buffer)
        logger.info(f"Reporte CSV: {csv_path}")

    zip_path = None
    if args.zip:
        zip_path = make_zip(lot_dir)
        size_mb = os.path.getsize(zip_path) / (1024 * 1024)
        logger.info(f"ZIP creado: {zip_path} ({size_mb:.2f} MB)")

    if args.send:
        to = os.getenv("CONTADORA_EMAIL") or cfg.get("contadora_email")
        if not to:
            logger.error("Falta CONTADORA_EMAIL en .env o 'contadora_email' en config.yaml")
            return
        if not zip_path:
            zip_path = make_zip(lot_dir)
        subject = f"Facturas DTE del {args.date_from} al {args.date_to}"
        body = (
            f"Adjunto ZIP con las facturas del {args.date_from} al {args.date_to}.\n\n"
            f"Carpeta de lote: {lot_dir}\n"
            f"Si necesitas los archivos individuales o el CSV de reporte, avísame."
        )
        from mailer import send_mail_with_attachment
        send_mail_with_attachment(gmail, to, subject, body, zip_path)
        logger.info(f"Correo enviado a: {to}")

    logger.info(f"TOTAL PDFs en rango: {total_pdfs}")

if __name__ == "__main__":
    main()
