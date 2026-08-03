from urllib.parse import quote

from bs4 import BeautifulSoup
from scrapers.base import KeywordSearchScraper, is_region_metropolitana
from scrapers.registry import register

# URL vieja (/trabajo/buscar?palabra=...) da 404 ahora — el sitio migró a esta ruta.
BASE_URL = "https://www.trabajando.cl/trabajo-empleo/{slug}"

# Mismo layout Vue que usan los portales corporativos de trabajando.cl (scrapers/portal_list.py):
# Selectores verificados en HTML real (2026-08-03).
SEL_CARD = "div.result-box"
SEL_TITULO = "h2 a"
SEL_EMPRESA = "span.type"
SEL_UBICACION = "span.location"
SEL_FECHA = "span.date"


@register("trabajando")
class TrabajandoScraper(KeywordSearchScraper):
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
            if not is_region_metropolitana(ubicacion):
                continue
            ofertas.append(
                self._make_oferta(titulo, empresa, ubicacion, fecha, "", url, "trabajando.cl")
            )
        return ofertas

    def fetch(self) -> list[dict]:
        try:
            from botasaurus.browser import browser, Driver, Wait
        except ImportError:
            print("[trabajando.cl] botasaurus no instalado. Ejecutar: pip install botasaurus")
            return []

        @browser(output=None, headless=False)
        def _fetch_page(driver: Driver, url: str) -> str:
            # trabajando.cl está detrás de Akamai, no Cloudflare — bypass_cloudflare=True
            # no aplica aquí. google_get() sin ese flag ya usa el "Humane Driver" de
            # Botasaurus (fingerprint no detectable + referrer de Google), que es la
            # estrategia general de la librería contra bot-management.
            driver.google_get(url)
            # Igual que laborum.cl: el listado se rellena vía fetch async del
            # cliente después de la carga inicial. Verificado en vivo: sin este
            # wait, la corrida es intermitente (a veces trae el listado, a veces
            # trae la página todavía sin resultados renderizados).
            driver.wait_for_element(SEL_CARD, wait=Wait.VERY_LONG)
            return driver.page_html

        ofertas = []
        for keyword in self.keywords:
            slug = quote(keyword.lower().replace(" ", "-"))
            url = BASE_URL.format(slug=slug)
            try:
                html = _fetch_page(url)
            except Exception as e:
                print(f"[trabajando.cl] {type(e).__name__} al buscar '{keyword}': {e}")
                continue
            if html:
                ofertas.extend(self._parse_html(html))
        return ofertas
