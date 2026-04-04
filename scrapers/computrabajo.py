import time
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from scrapers.base import BaseScraper, is_region_metropolitana

# Selectores verificados en HTML real (2026-04-03):
SEL_CARD = "article.box_offer"
SEL_TITULO = "h2 a"
SEL_EMPRESA = "p.dFlex"                   # párrafo con empresa (tiene clase dFlex)
SEL_UBICACION = "span.mr10:not(.fx_none)" # span de ubicación (excluye el span de rating)
SEL_FECHA = "p.fs13"                      # párrafo de fecha relativa

KEYWORD_SLUGS = {
    "Químico Farmacéutico": "qu%C3%ADmico-farmac%C3%A9utico",
    "QF": "qf",
}


class ComputrabajoScraper(BaseScraper):
    def _parse_html(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        ofertas = []
        for card in soup.select(SEL_CARD):
            titulo_tag = card.select_one(SEL_TITULO)
            if not titulo_tag:
                continue
            titulo = titulo_tag.get_text(strip=True)
            href = titulo_tag.get("href", "")
            url = f"https://cl.computrabajo.com{href}" if href.startswith("/") else href
            empresa = card.select_one(SEL_EMPRESA)
            empresa = empresa.get_text(strip=True) if empresa else ""
            ubicacion = card.select_one(SEL_UBICACION)
            ubicacion = ubicacion.get_text(strip=True) if ubicacion else ""
            fecha = card.select_one(SEL_FECHA)
            fecha = fecha.get_text(strip=True) if fecha else ""
            if not is_region_metropolitana(ubicacion):
                continue
            ofertas.append(
                self._make_oferta(titulo, empresa, ubicacion, fecha, "", url, "computrabajo.cl")
            )
        return ofertas

    def fetch(self) -> list[dict]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "es-CL,es;q=0.9",
        }
        ofertas = []
        for keyword, slug in KEYWORD_SLUGS.items():
            url = f"https://cl.computrabajo.com/trabajo-de-{slug}"
            params = {"where": "Región Metropolitana"}
            try:
                resp = requests.get(url, params=params, headers=headers, timeout=15)
                resp.raise_for_status()
            except requests.RequestException as e:
                print(f"[computrabajo.cl] Error al buscar '{keyword}': {e}")
                continue
            ofertas.extend(self._parse_html(resp.text))
            time.sleep(1)
        return ofertas
