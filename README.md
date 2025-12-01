¡Perfecto! 🚀 Te dejo un **README.md** inicial, bien organizado, para tu proyecto.

---

```markdown
# 🧾 DTE Bot – Descarga, ZIP y Envío de Facturas Electrónicas

Este proyecto automatiza la descarga de facturas electrónicas (DTE) desde Gmail, las organiza en carpetas por rango de fechas, genera un reporte CSV, comprime los archivos en un ZIP y opcionalmente los envía por correo a la contadora.

---

## 📂 Estructura del proyecto

```

facturas-bot/
│─ src/
│   ├─ main.py               # Punto de entrada (CLI)
│   ├─ gmail\_client.py       # Conexión Gmail API (buscar, leer, descargar)
│   ├─ filters.py            # Construcción de queries Gmail
│   ├─ storage.py            # Guardado en disco, CSV y ZIP
│   ├─ mailer.py             # Envío de correo con adjuntos
│   └─ logging\_conf.py       # Configuración de logs
│
│─ config/
│   ├─ config.yaml           # Configuración general (keywords, label, etc.)
│   └─ credentials/
│       ├─ credentials.json  # Clave OAuth (descargada de Google Cloud)
│       └─ token.pickle      # Token de autenticación (se genera solo)
│
│─ data/
│   ├─ downloads/            # PDFs descargados por rango
│   └─ out/                  # ZIPs generados
│
│─ ui\_app.py                 # Interfaz sencilla en Streamlit
│─ requirements.txt          # Dependencias del proyecto
│─ .env                      # Variables (ej: correo contadora)
│─ README.md

````

---

## ⚙️ Instalación

1. Clona este repo y entra a la carpeta:

```bash
git clone <url>
cd facturas-bot
````

2. Crea entorno virtual e instala dependencias:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Configura credenciales de Google:

   * Crea un proyecto en Google Cloud.
   * Habilita la **Gmail API**.
   * Crea credenciales OAuth de tipo **Desktop app**.
   * Descarga el JSON → guárdalo como:

     ```
     config/credentials/credentials.json
     ```

4. Archivo `.env`:

```env
CONTADORA_EMAIL=contadora@tuempresa.com
```

---

## 🚀 Uso por CLI

### Dry run (solo listar y contar PDFs)

```bash
python src/main.py --from 2025-08-01 --to 2025-08-31
```

### Descargar PDFs + CSV

```bash
python src/main.py --from 2025-08-01 --to 2025-08-31 --download
```

### Descargar + crear ZIP

```bash
python src/main.py --from 2025-08-01 --to 2025-08-31 --download --zip
```

### Descargar + ZIP + enviar a contadora

```bash
python src/main.py --from 2025-08-01 --to 2025-08-31 --download --zip --send
```

---

## 🖥️ Uso con Interfaz (UI)

Con **Streamlit** puedes usar una interfaz sencilla en el navegador:

```bash
streamlit run ui_app.py
```

* Selecciona rango de fechas.
* Marca opciones: Descargar, Crear ZIP, Enviar a contadora.
* (Opcional) Escribe una **Etiqueta de Gmail** para filtrar correos.

---

## 📝 Notas importantes

* Gmail bloquea adjuntos mayores a **25 MB**. Si tu ZIP se pasa de ese límite:

  * Usa rangos de fechas más pequeños, o
  * Modifica el proyecto para subir a Google Drive y enviar link (pendiente de implementar).
* El campo **Etiqueta de Gmail (opcional)** permite filtrar solo correos que tengan esa etiqueta en tu inbox.
* Los logs detallados se guardan en `logs/run_YYYY-MM-DD_HHMM.log`.


## 👤 Autor

Desarrollado para automatizar la gestión de facturas DTE y ahorrar tiempo en el proceso de descarga, organización y envío a la contadora.