"""
Scraper para Bolsa Nacional de Empleo (bne.cl)
El sitio renderiza resultados vía JavaScript — requiere Playwright.

Selectores verificados en HTML real (2026-04-05).
"""
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper, is_region_metropolitana

BASE_URL = "https://www.bne.cl/ofertas"
SEL_CARD      = "article.resultadoOfertas"
SEL_TITULO    = "div.tituloOferta a"
SEL_EMPRESA   = "div.datosEmpresaOferta div:first-child"
SEL_UBICACION = "div.datosEmpresaOferta div:last-child"
SEL_FECHA     = "span.fechaOferta"
SEL_DESC      = "div.descripcionOferta span"


class BneScraper(BaseScraper):
    def _parse_html(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        ofertas = []
        for card in soup.select(SEL_CARD):
            titulo_tag = card.select_one(SEL_TITULO)
            if not titulo_tag:
                continue
            titulo = titulo_tag.get_text(strip=True)
            href = titulo_tag.get("href", "")
            url = f"https://www.bne.cl{href}" if href.startswith("/") else href

            empresa_tag = card.select_one(SEL_EMPRESA)
            empresa = empresa_tag.get_text(strip=True) if empresa_tag else ""

            ubicacion_tag = card.select_one(SEL_UBICACION)
            ubicacion = ubicacion_tag.get_text(strip=True) if ubicacion_tag else ""

            fecha_tag = card.select_one(SEL_FECHA)
            fecha = fecha_tag.get_text(strip=True) if fecha_tag else ""

            desc_tag = card.select_one(SEL_DESC)
            descripcion = desc_tag.get_text(strip=True) if desc_tag else ""

            if not is_region_metropolitana(ubicacion):
                continue

            ofertas.append(
                self._make_oferta(titulo, empresa, ubicacion, fecha, descripcion, url, "bne.cl")
            )
        return ofertas

    def fetch(self) -> list[dict]:
        try:
            from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
        except ImportError:
            print("[bne.cl] playwright no instalado.")
            return []

        ofertas = []
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
            page.set_extra_http_headers({"Accept-Language": "es-CL,es;q=0.9"})

            for keyword in self.KEYWORDS:
                url = (
                    f"{BASE_URL}?mostrar=empleo"
                    f"&textoLibre={keyword.replace(' ', '%20')}"
                    f"&numResultadosPorPagina=50"
                    f"&clasificarYPaginar=true"
                )
                try:
                    page.goto(url, timeout=25000)
                    page.wait_for_load_state("networkidle", timeout=15000)
                    try:
                        page.wait_for_selector(SEL_CARD, timeout=10000)
                    except PWTimeout:
                        print(f"[bne.cl] Sin resultados visibles para '{keyword}'")
                        continue
                    ofertas.extend(self._parse_html(page.content()))
                except Exception as e:
                    print(f"[bne.cl] {type(e).__name__} al buscar '{keyword}': {e}")

            browser.close()

        return ofertas
