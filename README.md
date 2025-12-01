---

# 🧾 DTE Bot – Descarga, ZIP y envío de facturas electrónicas

Este proyecto automatiza la descarga de facturas (DTE) desde Gmail, las organiza por rango de fechas, genera un CSV, comprimo en ZIP y puedo enviarlas por correo a la contadora. Incluye CLI y una UI sencilla en Streamlit.

---

## 🧰 Qué hace
- Busca correos con adjuntos PDF/JSON usando palabras clave y rango de fechas.
- Deduplica adjuntos (estado en `data/state/processed.jsonl` y hashes por lote).
- Guarda PDFs/JSON en subcarpetas por correo y arma `reporte.csv`.
- Genera un ZIP del lote y, si quiero, lo envía por Gmail.

---

## 📂 Estructura
```
facturas-bot/
│─ src/
│   ├─ main.py            # CLI principal
│   ├─ gmail_client.py    # Gmail API (buscar, leer, descargar)
│   ├─ filters.py         # Construcción de queries Gmail
│   ├─ storage.py         # Guardado en disco, CSV y ZIP
│   ├─ mailer.py          # Envío de correo con adjuntos
│   └─ logging_conf.py    # Configuración de logs
│
│─ config/
│   ├─ config.yaml        # Keywords, label opcional, paths
│   └─ credentials/
│       ├─ credentials.json  # Clave OAuth (Google Cloud)
│       └─ token.pickle      # Token que se genera solo
│
│─ data/
│   ├─ downloads/         # PDFs/JSON por rango
│   └─ out/               # ZIPs generados
│
│─ ui_app.py              # Interfaz Streamlit
│─ requirements.txt       # Dependencias
│─ .env                   # Variables (ej: correo contadora)
│─ README.md
```

---

## 🔧 Requisitos
- Python 3.x
- Credenciales OAuth de Gmail (Desktop) habilitando Gmail API.
- Entorno virtual recomendado.

---

## ⚙️ Instalación
```bash
git clone <url>
cd facturas-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 🔑 Configuración
1) Credenciales: descarga el JSON de OAuth y guárdalo como `config/credentials/credentials.json`. El `token.pickle` se crea solo la primera vez que autorizo.

2) Variables de entorno (`.env`):
```env
CONTADORA_EMAIL=contadora@tuempresa.com
```

3) Ajustes en `config/config.yaml`: keywords, label opcional de Gmail, carpeta de salida, etc.

---

## 🚀 Uso por CLI
- Dry run (solo listar y contar PDFs):
```bash
python src/main.py --from 2025-08-01 --to 2025-08-31
```
- Descargar PDFs + CSV:
```bash
python src/main.py --from 2025-08-01 --to 2025-08-31 --download
```
- Descargar + ZIP:
```bash
python src/main.py --from 2025-08-01 --to 2025-08-31 --download --zip
```
- Descargar + ZIP + enviar a contadora:
```bash
python src/main.py --from 2025-08-01 --to 2025-08-31 --download --zip --send
```

---

## 🖥️ Uso con UI (Streamlit)
```bash
streamlit run ui_app.py
```
Selecciono fechas, marco Descargar/ZIP/Enviar, y opcionalmente paso una etiqueta de Gmail para filtrar. La app muestra progreso, genera el CSV/ZIP y puede enviar el correo.

---

## 📝 Notas
- Gmail bloquea adjuntos >25 MB. Si el ZIP pesa mucho, uso rangos más pequeños o evalúo subir a Drive y mandar link.
- Los logs quedan en `logs/run_YYYY-MM-DD_HHMM.log`.
- La deduplicación evita re-procesar adjuntos previos y dupes dentro del mismo lote.

---

## 👤 Autor
Armado para automatizar la gestión de facturas DTE y ahorrarme tiempo en descarga, organización y envío a la contadora.
