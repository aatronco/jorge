"""
Scraper para Bolsa Nacional de Empleo (bne.cl)
El sitio renderiza resultados vía JavaScript — requiere Playwright.

Selectores verificados: pendiente verificación en HTML real.
Si retorna 0 resultados, inspeccionar el DOM con DevTools y actualizar SEL_CARD.
"""
from scrapers.base import BaseScraper, is_region_metropolitana

BASE_URL = "https://www.bne.cl/ofertas"

# Selector del contenedor de cada oferta — ajustar si el sitio cambia
SEL_CARD = "div.oferta, li.oferta, article.oferta, div.card-oferta, div[class*='oferta']"
SEL_LOADING_DONE = "div.oferta, li.oferta, article.oferta, div.card-oferta, div[class*='oferta'], div.sin-resultados, p.sin-resultados"


class BneScraper(BaseScraper):
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
                    f"&codigoRegion=13"
                )
                try:
                    page.goto(url, timeout=25000)
                    page.wait_for_load_state("networkidle", timeout=15000)
                    # Esperar hasta que aparezcan resultados o mensaje de sin resultados
                    try:
                        page.wait_for_selector(SEL_LOADING_DONE, timeout=10000)
                    except PWTimeout:
                        pass

                    # Extraer datos directamente del DOM renderizado
                    results = page.evaluate("""() => {
                        const jobs = [];
                        // Intentar múltiples selectores comunes
                        const selectors = [
                            'div.oferta', 'li.oferta', 'article.oferta',
                            'div.card-oferta', 'div[class*="oferta-item"]',
                            'div[class*="job-card"]', 'div[class*="resultado"]',
                            'li[class*="oferta"]', 'article[class*="oferta"]',
                        ];
                        let cards = [];
                        for (const sel of selectors) {
                            cards = document.querySelectorAll(sel);
                            if (cards.length > 0) break;
                        }
                        cards.forEach(card => {
                            // Título: primer h2, h3, h4 o elemento con clase título
                            const titleEl = card.querySelector('h2, h3, h4, [class*="titulo"], [class*="title"], [class*="nombre-oferta"]');
                            const title = titleEl ? titleEl.innerText.trim() : '';
                            if (!title) return;
                            // Link
                            const linkEl = card.querySelector('a[href]');
                            const href = linkEl ? linkEl.getAttribute('href') : '';
                            const url = href.startsWith('http') ? href : 'https://www.bne.cl' + href;
                            // Empresa
                            const empresaEl = card.querySelector('[class*="empresa"], [class*="company"], [class*="razon-social"]');
                            const empresa = empresaEl ? empresaEl.innerText.trim() : '';
                            // Ubicación
                            const ubicEl = card.querySelector('[class*="ubicacion"], [class*="region"], [class*="ciudad"], [class*="lugar"]');
                            const ubicacion = ubicEl ? ubicEl.innerText.trim() : '';
                            // Fecha
                            const fechaEl = card.querySelector('[class*="fecha"], time, [class*="date"]');
                            const fecha = fechaEl ? (fechaEl.getAttribute('datetime') || fechaEl.innerText.trim()) : '';
                            jobs.push({ title, empresa, ubicacion, fecha, url });
                        });
                        return jobs;
                    }""")

                    for r in results:
                        if not r.get("title"):
                            continue
                        if not is_region_metropolitana(r.get("ubicacion", "")):
                            continue
                        ofertas.append(self._make_oferta(
                            r["title"],
                            r.get("empresa", ""),
                            r.get("ubicacion", ""),
                            r.get("fecha", ""),
                            "",
                            r.get("url", ""),
                            "bne.cl",
                        ))

                except Exception as e:
                    print(f"[bne.cl] {type(e).__name__} al buscar '{keyword}': {e}")

            browser.close()

        print(f"[bne.cl] {len(ofertas)} ofertas encontradas")
        return ofertas
