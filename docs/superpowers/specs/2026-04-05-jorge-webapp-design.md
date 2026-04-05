# Jorge — Web App + Google Sheets — Spec de Diseño

**Fecha:** 2026-04-05
**Proyecto:** jorge
**Objetivo:** Reemplazar el CSV local por un Google Sheet, agregar una web app (vanilla JS, GitHub Pages) con Google OAuth que muestre las ofertas organizadas por estado, y automatizar el scraper con GitHub Actions + botón de disparo desde la app.

---

## Contexto

El scraper existente recolecta ofertas de trabajo para QF en Chile y las guardaba en un CSV local. Se cambia el modelo para que:
1. El scraper escriba directamente a un Google Sheet via service account.
2. Una web app (mismo stack que nutrical) permita al usuario ver y gestionar el estado de cada oferta.
3. El scraper corra automáticamente en GitHub Actions (schedule diario + disparo manual desde la app).

---

## Arquitectura general

```
[Scraper Python]
      │  gspread + service account
      ▼
[Google Sheet del usuario]
      │  Sheets API v4 (OAuth token del browser)
      ▼
[Web App — GitHub Pages]
      │  GitHub API (PAT)
      ▼
[GitHub Actions — workflow_dispatch]
      │
      └─► [Scraper corre en CI]
```

---

## Sección 1: Scraper

### Cambios a `run.py`
- Reemplaza `guardar_csv()` por `guardar_sheet()` importado desde `sheets_writer.py`.
- `SHEET_ID` se lee desde variable de entorno (`os.environ["SHEET_ID"]`).

### Nuevo archivo `sheets_writer.py`
- Usa `gspread` + service account JSON (desde `GOOGLE_SERVICE_ACCOUNT_JSON` env var).
- Abre la sheet por ID. Si no existe la hoja `"Ofertas"`, la crea con los headers.
- Carga todas las URLs existentes en col F para deduplicar.
- Por cada oferta nueva: append de fila con `estado = "Nuevo"`.
- **Nunca sobreescribe** la columna `estado` de filas ya existentes.

### `requirements-scraper.txt`
Agrega:
```
gspread
google-auth
```

---

## Sección 2: GitHub Actions

### `.github/workflows/scraper.yml`

Triggers:
- `schedule`: cron diario a las 11:00 UTC (8am Chile)
- `workflow_dispatch`: disparo manual

Secrets requeridos en el repo:
- `GOOGLE_SERVICE_ACCOUNT_JSON` — contenido completo del JSON de la service account
- `SHEET_ID` — ID del Google Sheet

Steps:
1. `actions/checkout`
2. `actions/setup-python@v5` (Python 3.12)
3. `pip install -r requirements-scraper.txt`
4. `playwright install chromium` (si algún scraper lo necesita)
5. `python run.py`

---

## Sección 3: Web App

### Stack
Vanilla JS (ES modules), Google Identity Services (GIS) token flow, Sheets API v4, deploy estático en GitHub Pages. Sin framework, sin backend — igual que nutrical.

### Estructura de archivos

```
index.html
css/style.css
js/
  config.js        ← CLIENT_ID, GITHUB_REPO (owner/repo)
  auth.js          ← OAuth GIS (igual que nutrical)
  router.js        ← hash routing: #/login, #/setup, #/jobs
  sheets.js        ← leer ofertas, actualizar estado
  github.js        ← disparar workflow_dispatch via GitHub API
  views/
    login.js       ← pantalla de login con botón Google
    setup.js       ← prompt Sheet ID + prompt GitHub PAT
    jobs.js        ← panel principal con tabs
```

### Flujo de usuario

1. Usuario entra → sin token → `#/login`
2. Login con Google (GIS token flow)
3. Sin `spreadsheet_id` en `localStorage` → `#/setup`
   - Pega el Sheet ID → se valida leyendo la hoja → se guarda en `localStorage`
   - Pega GitHub PAT (scope `workflow`) → se guarda en `localStorage`
4. Con Sheet ID → `#/jobs`

### Vista `#/jobs`

- 3 tabs: **Nuevos** / **Postulados** / **Descartados**
- Cada aviso muestra: título, empresa, ubicación, fecha, fuente, link a la oferta
- Botones de cambio de estado: desde "Nuevo" → [Postular] [Descartar]; desde "Postulado" → [Descartar]; desde "Descartado" → [Restaurar]
- Cambio de estado: `PUT` a `Sheets API v4` en la celda H correspondiente
- Botón **"Actualizar"** en el navbar: llama `POST /repos/{owner}/{repo}/actions/workflows/scraper.yml/dispatches` con el PAT → GitHub Actions corre el scraper

### `js/sheets.js`

- `getJobs()` — lee `Ofertas!A2:H` completo, mapea a objetos
- `updateEstado(rowIndex, estado)` — `PUT` a `Ofertas!H{rowIndex}`
- `validateSpreadsheet(id)` — verifica que la hoja `Ofertas` existe y tiene headers

### `js/github.js`

- `triggerScraper()` — `POST` a GitHub API con el PAT almacenado en `localStorage`
- Muestra toast de confirmación o error

---

## Sección 4: Estructura del Google Sheet

**Nombre de hoja:** `Ofertas`

| Col | Campo | Descripción |
|-----|-------|-------------|
| A | `titulo` | Título del cargo |
| B | `empresa` | Nombre de la empresa |
| C | `ubicacion` | Ciudad/región |
| D | `fecha_publicacion` | Fecha ISO 8601 |
| E | `descripcion` | Descripción breve |
| F | `url` | URL de la oferta (clave de deduplicación) |
| G | `fuente` | Portal de origen |
| H | `estado` | `Nuevo` / `Postulado` / `Descartado` |

Fila 1: headers. El scraper escribe cols A–H al insertar. Solo toca `estado` al insertar (valor `"Nuevo"`). La web app solo escribe col H.

---

## Setup inicial (una sola vez)

1. Crear proyecto en Google Cloud Console, habilitar Sheets API, crear service account, descargar JSON.
2. Crear OAuth 2.0 Client ID (web application), agregar el dominio de GitHub Pages como origen autorizado.
3. Crear el Google Sheet manualmente (o dejar que el scraper lo cree en la primera ejecución).
4. Compartir el Sheet con el email de la service account (editor).
5. Agregar `GOOGLE_SERVICE_ACCOUNT_JSON` y `SHEET_ID` como secrets en el repo de GitHub.
6. Crear GitHub PAT con scope `workflow`.
7. Deploy de la web app en GitHub Pages.

---

## Criterios de éxito

- El scraper corre en GitHub Actions sin errores y agrega ofertas nuevas al Sheet sin tocar el estado de las existentes.
- La web app permite login, selección de sheet y visualización de ofertas en 3 tabs.
- Cambiar el estado desde la web app actualiza la celda H en el Sheet en tiempo real.
- El botón "Actualizar" dispara el workflow y el scraper corre correctamente.
