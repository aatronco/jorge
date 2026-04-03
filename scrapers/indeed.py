from bs4 import BeautifulSoup
from scrapers.base import BaseScraper, is_region_metropolitana

BASE_URL = "https://cl.indeed.com/jobs"

# Indeed cambia sus selectores frecuentemente.
# Si devuelve 0 resultados, correr: playwright codegen cl.indeed.com
# y buscar los elementos de las tarjetas de trabajo.
SEL_CARD = "div.job_seen_beacon"
SEL_TITULO = "h2.jobTitle span"
SEL_TITULO_LINK = "h2.jobTitle a"
SEL_EMPRESA = "span.companyName"
SEL_UBICACION = "div.companyLocation"
SEL_FECHA = "span.date"


class IndeedScraper(BaseScraper):
    def _parse_html(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        ofertas = []
        for card in soup.select(SEL_CARD):
            titulo_tag = card.select_one(SEL_TITULO)
            link_tag = card.select_one(SEL_TITULO_LINK)
            if not titulo_tag:
                continue
            titulo = titulo_tag.get_text(strip=True)
            href = link_tag.get("href", "") if link_tag else ""
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
            fecha = card.select_one(SEL_FECHA)
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
            with p.chromium.launch(headless=True) as browser:
                page = browser.new_page()
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
