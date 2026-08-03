from bs4 import BeautifulSoup
from scrapers.base import PortalListScraper as _PortalListScraperBase, is_region_metropolitana
from scrapers.registry import register

SEL_CARD      = "div.result-box"
SEL_TITULO    = "h2 a"
SEL_EMPRESA   = "span.type"
SEL_UBICACION = "span.location"
SEL_FECHA     = "div.date"


@register("portal_list")
class PortalListScraper(_PortalListScraperBase):
    """
    Scraper genérico para portales que comparten el layout de trabajando.cl
    (corporativos o públicos). Cada institución en `self.portales` es un dict
    con `nombre`, `base_url`, `fuente`.
    """

    def _parse_html(self, html: str, base_url: str, fuente: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        ofertas = []
        for card in soup.select(SEL_CARD):
            titulo_el = card.select_one(SEL_TITULO)
            if not titulo_el:
                continue
            titulo = titulo_el.get_text(strip=True)
            if not any(kw.lower() in titulo.lower() for kw in self.keywords):
                continue
            href = titulo_el.get("href", "")
            url = base_url + href if href.startswith("/") else href
            empresa_el = card.select_one(SEL_EMPRESA)
            empresa = empresa_el.get_text(strip=True) if empresa_el else ""
            ubicacion_el = card.select_one(SEL_UBICACION)
            ubicacion = ubicacion_el.get_text(strip=True) if ubicacion_el else ""
            if not is_region_metropolitana(ubicacion):
                continue
            fecha_el = card.select_one(SEL_FECHA)
            fecha = fecha_el.get_text(strip=True) if fecha_el else ""
            ofertas.append(
                self._make_oferta(titulo, empresa, ubicacion, fecha, "", url, fuente)
            )
        return ofertas

    def fetch(self) -> list[dict]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("[portal_list] playwright no instalado. Ejecutar: playwright install chromium")
            return []

        ofertas = []
        for portal in self.portales:
            base_url = portal["base_url"].rstrip("/")
            fuente = portal["fuente"]
            list_url = base_url + "/trabajo-empleo/"
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(
                        headless=True,
                        args=["--disable-blink-features=AutomationControlled"],
                    )
                    ctx = browser.new_context(
                        viewport={"width": 1280, "height": 900},
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    )
                    page = ctx.new_page()
                    page.add_init_script(
                        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                    )
                    page.goto(list_url, wait_until="networkidle", timeout=30000)
                    html = page.content()
                    browser.close()
            except Exception as e:
                print(f"[{fuente}] Error al cargar página: {e}")
                continue
            ofertas.extend(self._parse_html(html, base_url, fuente))
        return ofertas
