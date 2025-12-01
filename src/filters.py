from datetime import datetime, timedelta

def build_gmail_query(keywords, date_from, date_to, label=None):
    def fmt(d: datetime) -> str:
        return d.strftime("%Y/%m/%d")

    df = datetime.fromisoformat(date_from)
    dt = datetime.fromisoformat(date_to) + timedelta(days=1)  # incluir día final

    kw_or = " OR ".join([f'"{k}"' if " " in k else k for k in keywords])
    date_part = f" after:{fmt(df)} before:{fmt(dt)}"
    attach = " has:attachment (filename:pdf OR filename:json)"
    subject = f" subject:({kw_or})"
    lab = f' label:\"{label}\"' if label else ""

    return (subject + attach + date_part + lab).strip()
