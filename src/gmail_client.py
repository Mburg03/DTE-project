import os, pickle, base64
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


def get_gmail_service(
    creds_path="config/credentials/credentials.json",
    token_path="config/credentials/token.pickle",
):
    creds = None
    if os.path.exists(token_path):
        with open(token_path, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)

        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        with open(token_path, "wb") as f:
            pickle.dump(creds, f)

    return build("gmail", "v1", credentials=creds)


def search_messages(gmail, query, max_results=100):
    res = (
        gmail.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )
    messages = res.get("messages", [])
    next_token = res.get("nextPageToken")

    while next_token:
        res = (
            gmail.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results, pageToken=next_token)
            .execute()
        )
        messages.extend(res.get("messages", []))
        next_token = res.get("nextPageToken")

    return [m["id"] for m in messages]


def get_message(gmail, msg_id):
    return gmail.users().messages().get(userId="me", id=msg_id, format="full").execute()


def count_pdf_attachments(message):
    count = 0
    payload = message.get("payload", {})
    parts = payload.get("parts", []) or []
    stack = parts[:]
    while stack:
        p = stack.pop()
        if p.get("mimeType", "").startswith("multipart/") and p.get("parts"):
            stack.extend(p["parts"])
        else:
            fname = p.get("filename") or ""
            if fname.lower().endswith(".pdf"):
                count += 1
    return count

# --- NUEVO: recorrer partes y localizar adjuntos ---
def _iter_parts(payload):
    """Recorre recursivamente las partes del mensaje."""
    stack = list(payload.get("parts", []) or [])
    while stack:
        p = stack.pop()
        if p.get("mimeType", "").startswith("multipart/") and p.get("parts"):
            stack.extend(p["parts"])
        else:
            yield p


# --- NUEVO: descarga SOLO PDFs, devuelve bytes en memoria ---
def download_pdf_attachments(gmail, message):
    """
    Devuelve una lista de diccionarios:
    [
      {
        "filename": "Factura_123.pdf",
        "attachment_id": "...",
        "data": b"<bytes del pdf>"
      },
      ...
    ]
    """
    results = []
    payload = message.get("payload", {}) or {}

    for part in _iter_parts(payload):
        fname = (part.get("filename") or "").strip()
        if not fname or not fname.lower().endswith(".pdf"):
            continue

        body = part.get("body", {}) or {}
        att_id = body.get("attachmentId")
        if not att_id:
            # a veces el PDF viene inline sin attachmentId; lo ignoramos por simplicidad
            continue

        att = gmail.users().messages().attachments().get(
            userId="me",
            messageId=message["id"],
            id=att_id
        ).execute()

        # Gmail retorna base64-url-safe
        file_bytes = base64.urlsafe_b64decode(att["data"].encode("utf-8"))
        results.append({
            "filename": fname,
            "attachment_id": att_id,
            "data": file_bytes,
        })

    return results

# -- NUEVO: descarga adjuntos con extensiones específicas --
def download_attachments(gmail, message, exts=("pdf", "json")):
    """
    Devuelve lista de adjuntos cuyas extensiones estén en exts.
    [{filename, attachment_id, data}]
    """
    results = []
    payload = message.get("payload", {}) or {}
    for part in _iter_parts(payload):
        fname = (part.get("filename") or "").strip()
        if not fname:
            continue
        if not any(fname.lower().endswith(f".{e}") for e in exts):
            continue
        body = part.get("body", {}) or {}
        att_id = body.get("attachmentId")
        if not att_id:
            continue
        att = gmail.users().messages().attachments().get(
            userId="me", messageId=message["id"], id=att_id
        ).execute()
        file_bytes = base64.urlsafe_b64decode(att["data"].encode("utf-8"))
        results.append({"filename": fname, "attachment_id": att_id, "data": file_bytes})
    return results
