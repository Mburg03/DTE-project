# ui_app.py
import streamlit as st
import os, yaml
from datetime import date

from src.filters import build_gmail_query
from src.gmail_client import (
    get_gmail_service, search_messages, get_message,
    count_pdf_attachments, download_attachments
)
from src.storage import (
    ensure_lot_dir, ensure_message_dir,
    build_standard_filename, save_pdf_bytes,
    append_csv_report, make_zip,
    sha256_bytes, load_hash_index, save_hash_index
)
from src.state import load_processed, append_processed
from src.mailer import send_mail_with_attachment

# cargar config
with open("config/config.yaml", "r", encoding="utf-8") as f:
    CFG = yaml.safe_load(f)

st.set_page_config(page_title="DTE Bot – Descarga, ZIP y Envío", page_icon="🧾")

st.title("🧾 DTE Bot – Descarga, ZIP y Envío")

col1, col2 = st.columns(2)
with col1:
    date_from = st.date_input("Desde (YYYY-MM-DD)", value=date.today())
with col2:
    date_to = st.date_input("Hasta (YYYY-MM-DD)", value=date.today())

do_download = st.checkbox("Descargar PDFs", value=True)
do_zip = st.checkbox("Crear ZIP", value=True)
do_send = st.checkbox("Enviar a contadora", value=False)

to_email = st.text_input(
    "Email contadora",
    value=os.getenv("CONTADORA_EMAIL") or CFG.get("contadora_email", "")
)

if st.button("Ejecutar"):
    gmail = get_gmail_service()
    query = build_gmail_query(
        CFG["keywords"],
        str(date_from),
        str(date_to),
    )
    st.write("**Query usada:**", query)

    ids = search_messages(gmail, query, max_results=CFG.get("max_results", 100))
    st.write(f"Se encontraron {len(ids)} mensajes.")

    lot_dir = ensure_lot_dir(CFG.get("output_dir", "data"), str(date_from), str(date_to))
    state_path = "data/state/processed.jsonl"
    seen = load_processed(state_path)
    lot_hashes = load_hash_index(lot_dir)

    csv_rows, processed_keys = [], []
    total_pdfs = 0

    progress = st.progress(0)
    log_box = st.empty()

    for i, mid in enumerate(ids, 1):
        msg = get_message(gmail, mid)
        headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}
        subj, frm = headers.get("subject", "(sin asunto)"), headers.get("from", "(sin remitente)")
        pdfs = count_pdf_attachments(msg)
        total_pdfs += pdfs

        log_box.text(f"[{i}/{len(ids)}] PDFs:{pdfs} From:{frm} | {subj}")
        progress.progress(i / len(ids))

        atts = download_attachments(gmail, msg, exts=("pdf", "json"))
        if do_download and atts:
            msg_dir = ensure_message_dir(lot_dir, msg)
            for a in atts:
                key = f"{mid}:{a['attachment_id']}"
                if key in seen:
                    continue
                h = sha256_bytes(a["data"])
                if h in lot_hashes:
                    processed_keys.append(key)
                    continue
                std = build_standard_filename(msg, a["filename"])
                out = save_pdf_bytes(msg_dir, std, a["data"])
                lot_hashes.add(h)
                processed_keys.append(key)
                csv_rows.append({
                    "fecha": std[:8],
                    "remitente": frm,
                    "asunto": subj,
                    "archivo_local": out,
                    "messageId": mid,
                    "attachmentId": a["attachment_id"],
                })

    if do_download and csv_rows:
        csv_path = append_csv_report(lot_dir, csv_rows)
        st.success(f"Reporte generado: {csv_path}")

    zip_path = None
    if do_zip or do_send:
        zip_path = make_zip(lot_dir)
        st.success(f"ZIP generado: {zip_path}")

    if processed_keys:
        append_processed(state_path, processed_keys)
        save_hash_index(lot_dir, lot_hashes)

    if do_send:
        if not to_email:
            st.error("Falta correo de contadora.")
        else:
            subject = f"Facturas DTE del {date_from} al {date_to}"
            body = f"Adjunto ZIP del rango {date_from} a {date_to}.\nCarpeta: {lot_dir}"
            send_mail_with_attachment(gmail, to_email, subject, body, zip_path)
            st.success(f"Enviado a: {to_email}")

    st.info(f"Total PDFs: {total_pdfs}")
    st.balloons()