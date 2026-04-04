import time
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from scrapers.base import BaseScraper, is_region_metropolitana

BASE_URL = "https://www.trabajando.cl/trabajo/buscar"
REGION_PARAM = "Región Metropolitana"

SEL_CARD = "div.aviso-wrap"
SEL_TITULO = "h2.aviso-titulo a"
SEL_EMPRESA = "span.empresa-nombre"
SEL_UBICACION = "span.lugar"
SEL_FECHA = "span.fecha-publicacion"
SEL_DESC = "p.descripcion-corta"


class TrabajandoScraper(BaseScraper):
    def _parse_html(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        ofertas = []
        for card in soup.select(SEL_CARD):
            titulo_tag = card.select_one(SEL_TITULO)
            if not titulo_tag:
                continue
            titulo = titulo_tag.get_text(strip=True)
            href = titulo_tag.get("href", "")
            url = f"https://www.trabajando.cl{href}" if href.startswith("/") else href
            empresa = card.select_one(SEL_EMPRESA)
            empresa = empresa.get_text(strip=True) if empresa else ""
            ubicacion = card.select_one(SEL_UBICACION)
            ubicacion = ubicacion.get_text(strip=True) if ubicacion else ""
            fecha = card.select_one(SEL_FECHA)
            fecha = fecha.get_text(strip=True) if fecha else ""
            desc = card.select_one(SEL_DESC)
            desc = desc.get_text(strip=True) if desc else ""
            if not is_region_metropolitana(ubicacion):
                continue
            ofertas.append(
                self._make_oferta(titulo, empresa, ubicacion, fecha, desc, url, "trabajando.cl")
            )
        return ofertas

    def fetch(self) -> list[dict]:
        # trabajando.cl es una SPA Nuxt que bloquea headless browsers.
        # El HTML estático no contiene datos de ofertas.
        # TODO: investigar API interna o alternativas de scraping.
        print("[trabajando.cl] Sitio bloquea automatización. Skipping.")
        return []
