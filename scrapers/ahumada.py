import requests
from bs4 import BeautifulSoup
from scrapers.base import BaseScraper, is_region_metropolitana

URL = "https://farmaciasahumada.buk.cl/trabaja-con-nosotros"

SEL_CARD      = "div.jobs__card"
SEL_TITULO    = "b.fw-700"
SEL_UBICACION = "div.jobs__card-info span"
SEL_URL       = "a[href*='/s/']"

KEYWORDS_QF = ["químico", "farmacéutico", "q.f.", "regente", "bioquímico"]


class AhumadaScraper(BaseScraper):
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
            ubicacion_el = card.select_one(SEL_UBICACION)
            ubicacion = ubicacion_el.get_text(strip=True) if ubicacion_el else ""
            if not is_region_metropolitana(ubicacion):
                continue
            # fecha: buscar el span que contiene "Proceso iniciado"
            fecha = ""
            for span in card.find_all("span"):
                text = span.get_text(strip=True)
                if "proceso" in text.lower() or "iniciado" in text.lower():
                    fecha = text
                    break
            url_el = card.select_one(SEL_URL)
            url = url_el.get("href", "") if url_el else ""
            ofertas.append(
                self._make_oferta(titulo, "Farmacias Ahumada", ubicacion, fecha, "", url, "farmaciasahumada.cl")
            )
        return ofertas

    def fetch(self) -> list[dict]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "es-CL,es;q=0.9",
        }
        try:
            resp = requests.get(URL, headers=headers, timeout=20)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"[farmaciasahumada.cl] Error al obtener empleos: {e}")
            return []
        return self._parse_html(resp.text)
