import time
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from scrapers.base import BaseScraper, is_region_metropolitana

BASE_URL = "https://www.laborum.com/empleos"

# Verificar en https://www.laborum.com si los selectores cambian:
SEL_CARD = "div.aviso-item"
SEL_TITULO = "a.titulo-aviso"
SEL_EMPRESA = "span.empresa"
SEL_UBICACION = "span.localidad"
SEL_FECHA = "span.fecha"
SEL_DESC = "p.extracto"


class LaborumScraper(BaseScraper):
    def _parse_html(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        ofertas = []
        for card in soup.select(SEL_CARD):
            titulo_tag = card.select_one(SEL_TITULO)
            if not titulo_tag:
                continue
            titulo = titulo_tag.get_text(strip=True)
            href = titulo_tag.get("href", "")
            url = f"https://www.laborum.com{href}" if href.startswith("/") else href
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
                self._make_oferta(titulo, empresa, ubicacion, fecha, desc, url, "laborum.com")
            )
        return ofertas

    def fetch(self) -> list[dict]:
        # laborum.com es una SPA React con API protegida (403 en endpoints internos).
        # Headless browsers son bloqueados activamente.
        # TODO: investigar API interna o alternativas de scraping.
        print("[laborum.com] Sitio bloquea automatización. Skipping.")
        return []
