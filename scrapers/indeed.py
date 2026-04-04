from bs4 import BeautifulSoup
from scrapers.base import BaseScraper, is_region_metropolitana

BASE_URL = "https://cl.indeed.com/jobs"

# Selectores verificados en HTML real con anti-detección (2026-04-03).
# Indeed cambia selectores frecuentemente — re-verificar si vuelve a dar 0 resultados.
SEL_CARD = "div.result"
SEL_TITULO = "h2.jobTitle a"
SEL_EMPRESA = "span[data-testid='company-name']"
SEL_UBICACION = "div[data-testid='text-location']"
SEL_FECHA = ""  # indeed.cl no muestra fecha en la vista de lista


class IndeedScraper(BaseScraper):
    def _parse_html(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        ofertas = []
        for card in soup.select(SEL_CARD):
            titulo_tag = card.select_one(SEL_TITULO)
            if not titulo_tag:
                continue
            titulo = titulo_tag.get_text(strip=True)
            href = titulo_tag.get("href", "")
            if href.startswith("/"):
                url = f"https://cl.indeed.com{href}"
            elif href.startswith("http"):
                url = href
            else:
                url = f"https://cl.indeed.com/viewjob?jk={href}"
            empresa = card.select_one(SEL_EMPRESA)
            empresa = empresa.get_text(strip=True) if empresa else ""
            ubicacion = card.select_one(SEL_UBICACION)
            ubicacion = ubicacion.get_text(strip=True) if ubicacion else ""
            fecha = card.select_one(SEL_FECHA) if SEL_FECHA else None
            fecha = fecha.get_text(strip=True) if fecha else ""
            if not is_region_metropolitana(ubicacion):
                continue
            ofertas.append(
                self._make_oferta(titulo, empresa, ubicacion, fecha, "", url, "indeed.cl")
            )
        return ofertas

    def fetch(self) -> list[dict]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("[indeed.cl] playwright no instalado. Ejecutar: playwright install chromium")
            return []

        from urllib.parse import urlencode

        ofertas = []
        with sync_playwright() as p:
            with p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            ) as browser:
                ctx = browser.new_context(
                    viewport={"width": 1280, "height": 900},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                )
                page = ctx.new_page()
                page.add_init_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                )
                page.set_extra_http_headers({"Accept-Language": "es-CL,es;q=0.9"})
                for keyword in self.KEYWORDS:
                    try:
                        params = urlencode({"q": keyword, "l": "Región Metropolitana, Chile"})
                        url = f"{BASE_URL}?{params}"
                        page.goto(url, timeout=20000)
                        page.wait_for_selector(SEL_CARD, timeout=10000)
                        html = page.content()
                        ofertas.extend(self._parse_html(html))
                    except Exception as e:
                        print(f"[indeed.cl] {type(e).__name__} al buscar '{keyword}': {e}")
        return ofertas
