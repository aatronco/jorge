from urllib.parse import quote

from bs4 import BeautifulSoup
from scrapers.base import KeywordSearchScraper, is_region_metropolitana
from scrapers.registry import register

BASE_URL = "https://www.laborum.cl/empleos-busqueda-{slug}.html"

# laborum.cl es una SPA (styled-components: clases dinámicas, no confiables).
# Los IDs sí son estables entre despliegues (prefijo fijo + id numérico de la oferta):
# Selectores verificados en HTML real (2026-08-03).
SEL_CARD = 'a[aria-labelledby^="header-col-job-posting-"]'
SEL_HEADER = '[id^="header-col-job-posting-"]'
SEL_DATA = '[id^="data-col-job-posting-"]'


@register("laborum")
class LaborumScraper(KeywordSearchScraper):
    def _parse_html(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        ofertas = []
        for card in soup.select(SEL_CARD):
            header = card.select_one(SEL_HEADER)
            if not header:
                continue
            titulo_el = header.select_one("h2")
            if not titulo_el:
                continue
            titulo = titulo_el.get_text(strip=True)
            h3s = header.select("h3")
            fecha = h3s[0].get_text(strip=True) if len(h3s) > 0 else ""
            empresa = h3s[1].get_text(strip=True) if len(h3s) > 1 else ""
            data_el = card.select_one(SEL_DATA)
            ubicacion_el = data_el.select_one("span") if data_el else None
            ubicacion = ubicacion_el.get_text(strip=True) if ubicacion_el else ""
            if not is_region_metropolitana(ubicacion):
                continue
            href = card.get("href", "")
            url = f"https://www.laborum.cl{href}" if href.startswith("/") else href
            ofertas.append(
                self._make_oferta(titulo, empresa, ubicacion, fecha, "", url, "laborum.cl")
            )
        return ofertas

    def fetch(self) -> list[dict]:
        try:
            from botasaurus.browser import browser, Driver, Wait
        except ImportError:
            print("[laborum.cl] botasaurus no instalado. Ejecutar: pip install botasaurus")
            return []

        # headless=False es obligatorio: Botasaurus advierte que en modo headless
        # Cloudflare/Datadome detectan el navegador de todas formas. Esto abre una
        # ventana de Chrome real al correr el scraper — no sirve en un servidor sin
        # display (por eso el workflow de CI se eliminó; este scraper es local-only).
        @browser(output=None, headless=False)
        def _fetch_page(driver: Driver, url: str) -> str:
            # laborum.cl está detrás de Cloudflare Bot Management (cookie __cf_bm
            # confirmada en headers de respuesta) — bypass_cloudflare=True es la
            # estrategia documentada de Botasaurus para este caso específico.
            driver.google_get(url, bypass_cloudflare=True)
            # google_get() retorna apenas el DOM inicial carga — el listado de
            # ofertas se rellena después vía fetch async del lado del cliente
            # (verificado en vivo: sin este wait, page_html trae "Buscando
            # ofertas de empleo", la pantalla de carga, en vez de resultados
            # reales). Si no hay resultados para la keyword, esto lanza
            # TimeoutError y el caller lo trata como "sin ofertas".
            driver.wait_for_element(SEL_HEADER, wait=Wait.VERY_LONG)
            return driver.page_html

        ofertas = []
        for keyword in self.keywords:
            slug = quote(keyword.lower().replace(" ", "-"))
            url = BASE_URL.format(slug=slug)
            try:
                html = _fetch_page(url)
            except Exception as e:
                print(f"[laborum.cl] {type(e).__name__} al buscar '{keyword}': {e}")
                continue
            if html:
                ofertas.extend(self._parse_html(html))
        return ofertas
