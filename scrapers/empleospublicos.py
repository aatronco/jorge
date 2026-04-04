import time
import requests
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper

BASE_CONV = "https://www.empleospublicos.cl/pub/convocatorias/"
SEARCH_URL = BASE_CONV + "convocatorias.aspx"

SEL_CARD   = "div.caja.row"
SEL_TITULO = "#bx_titulos"
SEL_EMPRESA = "#bx_resumen strong"
SEL_FECHA  = "#bx_resumen em"
SEL_DESC   = "#bx_resumen"
SEL_URL    = "a.btnverficha"

KEYWORDS_QF = ["químico", "farmacéutico", "q.f.", "regente", "bioquímico"]

SEARCH_TERMS = [
    "qu%C3%ADmico+farmac%C3%A9utico",
    "farmac%C3%A9utico+regente",
]


class EmpleosPublicosScraper(BaseScraper):
    def _parse_html(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        ofertas = []
        seen_urls: set[str] = set()
        for card in soup.select(SEL_CARD):
            titulo_el = card.select_one(SEL_TITULO)
            if not titulo_el:
                continue
            titulo = titulo_el.get_text(strip=True)
            # Filtrar por keyword QF en el título
            if not any(kw in titulo.lower() for kw in KEYWORDS_QF):
                continue
            empresa_el = card.select_one(SEL_EMPRESA)
            empresa = empresa_el.get_text(strip=True) if empresa_el else ""
            fecha_el = card.select_one(SEL_FECHA)
            fecha = fecha_el.get_text(strip=True) if fecha_el else ""
            desc_el = card.select_one(SEL_DESC)
            desc = ""
            if desc_el:
                raw = desc_el.get_text(separator=" ", strip=True)
                raw = raw.replace(empresa, "").replace(fecha, "").strip()
                desc = " ".join(raw.split())
            url_el = card.select_one(SEL_URL)
            href = url_el.get("href", "") if url_el else ""
            url = BASE_CONV + href if href and not href.startswith("http") else href
            if url in seen_urls:
                continue
            seen_urls.add(url)
            # ubicacion vacío → is_region_metropolitana devuelve True (incluir todos los empleos públicos QF)
            ofertas.append(
                self._make_oferta(titulo, empresa, "", fecha, desc, url, "empleospublicos.cl")
            )
        return ofertas

    def fetch(self) -> list[dict]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "es-CL,es;q=0.9",
        }
        all_offers: list[dict] = []
        seen_urls: set[str] = set()
        for term in SEARCH_TERMS:
            url = f"{SEARCH_URL}?busqueda={term}"
            try:
                resp = requests.get(url, headers=headers, timeout=20)
                resp.raise_for_status()
            except requests.RequestException as e:
                print(f"[empleospublicos.cl] Error al buscar '{term}': {e}")
                continue
            for oferta in self._parse_html(resp.text):
                if oferta["url"] not in seen_urls:
                    seen_urls.add(oferta["url"])
                    all_offers.append(oferta)
            time.sleep(1)
        return all_offers
