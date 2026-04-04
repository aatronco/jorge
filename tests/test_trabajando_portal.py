from pathlib import Path
from scrapers.trabajando_portal import TrabajandoPortalScraper

FIXTURE = (Path(__file__).parent / "fixtures" / "trabajando_portal_sample.html").read_text(encoding="utf-8")
BASE_URL = "https://clinicaalemana.trabajando.cl"


def test_parse_filtra_qf():
    scraper = TrabajandoPortalScraper(BASE_URL, "clinicaalemana.cl")
    ofertas = scraper._parse_html(FIXTURE)
    # fixture: 1 QF en RM, 1 no-QF RM excluido, 1 QF fuera RM excluido
    assert len(ofertas) == 1
    assert "Químico" in ofertas[0]["titulo"]


def test_parse_excluye_no_qf():
    scraper = TrabajandoPortalScraper(BASE_URL, "clinicaalemana.cl")
    ofertas = scraper._parse_html(FIXTURE)
    assert not any("Data Governance" in o["titulo"] for o in ofertas)


def test_parse_excluye_fuera_rm():
    scraper = TrabajandoPortalScraper(BASE_URL, "clinicaalemana.cl")
    ofertas = scraper._parse_html(FIXTURE)
    assert not any("Concepción" in o["ubicacion"] for o in ofertas)


def test_parse_estructura_oferta():
    scraper = TrabajandoPortalScraper(BASE_URL, "clinicaalemana.cl")
    ofertas = scraper._parse_html(FIXTURE)
    assert len(ofertas) > 0
    oferta = ofertas[0]
    assert set(oferta.keys()) == {
        "titulo", "empresa", "ubicacion", "fecha_publicacion", "descripcion", "url", "fuente"
    }
    assert oferta["fuente"] == "clinicaalemana.cl"
    assert oferta["url"] == BASE_URL + "/trabajo/6052722-quimico-a-farmaceutico-a"
    assert "Vitacura" in oferta["ubicacion"]
    assert oferta["fecha_publicacion"] == "Hace 3 días"
