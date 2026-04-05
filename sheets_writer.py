import json
import os

import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_NAME = "Ofertas"
HEADERS = [
    "titulo", "empresa", "ubicacion", "fecha_publicacion",
    "descripcion", "url", "fuente", "estado",
]


def _get_client() -> gspread.Client:
    raw = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    info = json.loads(raw)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)


def guardar_sheet(ofertas: list[dict]) -> int:
    """Agrega ofertas nuevas al Google Sheet. Nunca sobreescribe el estado existente.

    Returns:
        Número de filas nuevas agregadas.
    """
    sheet_id = os.environ["SHEET_ID"]
    gc = _get_client()
    sh = gc.open_by_key(sheet_id)

    try:
        ws = sh.worksheet(SHEET_NAME)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(SHEET_NAME, rows=1000, cols=len(HEADERS))
        ws.append_row(HEADERS)

    existing = ws.get_all_records()
    existing_urls = {r["url"] for r in existing if r.get("url")}

    nuevas = [o for o in ofertas if o.get("url") and o["url"] not in existing_urls]
    if not nuevas:
        return 0

    rows = [
        [o.get(h, "") for h in HEADERS[:-1]] + ["Nuevo"]
        for o in nuevas
    ]
    ws.append_rows(rows, value_input_option="RAW")
    return len(nuevas)
