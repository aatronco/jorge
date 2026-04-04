from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper, is_region_metropolitana

SEL_CARD      = "div.result-box"
SEL_TITULO    = "h2 a"
SEL_EMPRESA   = "span.type"
SEL_UBICACION = "span.location"
SEL_FECHA     = "div.date"

KEYWORDS_QF = ["químico", "farmacéutico", "q.f.", "regente farmacia", "bioquímico"]

# Instituciones de salud con portal en trabajando.cl
PORTALES = {
    "clinicaalemana":  ("https://clinicaalemana.trabajando.cl",  "clinicaalemana.cl"),
    "bupa":            ("https://bupa.trabajando.cl",            "bupa.cl"),
    "redsalud":        ("https://redsalud.trabajando.cl",        "redsalud.cl"),
    "banmedica":       ("https://banmedica.trabajando.cl",       "banmedica.cl"),
    "colmena":         ("https://colmena.trabajando.cl",         "colmena.cl"),
    "clinicasantamaria": ("https://clinicasantamaria.trabajando.cl", "clinicasantamaria.cl"),
    "salcobrand":      ("https://empresassb.trabajando.cl",      "salcobrand.cl"),
}


class TrabajandoPortalScraper(BaseScraper):
    """
    Scraper genérico para portales corporativos de trabajando.cl.
    Cada empresa de salud tiene su propio subdominio con el mismo layout.
    Filtra por keywords QF en el título; acepta todos los resultados RM.
    """

    def __init__(self, base_url: str, fuente: str):
        self.base_url = base_url.rstrip("/")
        self.fuente = fuente

    def _parse_html(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        ofertas = []
        for card in soup.select(SEL_CARD):
            titulo_el = card.select_one(SEL_TITULO)
            if not titulo_el:
                continue
            titulo = titulo_el.get_text(strip=True)
            if not any(kw in titulo.lower() for kw in KEYWORDS_QF):
                continue
            href = titulo_el.get("href", "")
            url = self.base_url + href if href.startswith("/") else href
            empresa_el = card.select_one(SEL_EMPRESA)
            empresa = empresa_el.get_text(strip=True) if empresa_el else ""
            ubicacion_el = card.select_one(SEL_UBICACION)
            ubicacion = ubicacion_el.get_text(strip=True) if ubicacion_el else ""
            if not is_region_metropolitana(ubicacion):
                continue
            fecha_el = card.select_one(SEL_FECHA)
            fecha = fecha_el.get_text(strip=True) if fecha_el else ""
            ofertas.append(
                self._make_oferta(titulo, empresa, ubicacion, fecha, "", url, self.fuente)
            )
        return ofertas

    def fetch(self) -> list[dict]:
        list_url = self.base_url + "/trabajo-empleo/"
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
            print(f"[{self.fuente}] Error al cargar página: {e}")
            return []
        return self._parse_html(html)
