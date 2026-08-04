from pathlib import Path
from scrapers.portal_list import PortalListScraper

FIXTURE = (Path(__file__).parent / "fixtures" / "portal_list_sample.html").read_text(encoding="utf-8")
BASE_URL = "https://clinicaalemana.trabajando.cl"
KEYWORDS = ["Químico", "Farmacéutico", "Regente Farmacia", "Bioquímico"]


def _make_scraper():
    return PortalListScraper(
        keywords=KEYWORDS,
        portales=[{"nombre": "clinicaalemana", "base_url": BASE_URL, "fuente": "clinicaalemana.cl"}],
    )


def test_parse_filtra_qf():
    scraper = _make_scraper()
    ofertas = scraper._parse_html(FIXTURE, BASE_URL, "clinicaalemana.cl")
    # fixture: 1 QF en RM, 1 no-QF RM excluido, 1 QF fuera RM excluido
    assert len(ofertas) == 1
    assert "Químico" in ofertas[0]["titulo"]


def test_parse_excluye_no_qf():
    scraper = _make_scraper()
    ofertas = scraper._parse_html(FIXTURE, BASE_URL, "clinicaalemana.cl")
    assert not any("Data Governance" in o["titulo"] for o in ofertas)


def test_parse_excluye_fuera_rm():
    scraper = _make_scraper()
    ofertas = scraper._parse_html(FIXTURE, BASE_URL, "clinicaalemana.cl")
    assert not any("Concepción" in o["ubicacion"] for o in ofertas)


def test_parse_estructura_oferta():
    scraper = _make_scraper()
    ofertas = scraper._parse_html(FIXTURE, BASE_URL, "clinicaalemana.cl")
    assert len(ofertas) > 0
    oferta = ofertas[0]
    assert set(oferta.keys()) == {
        "titulo", "empresa", "ubicacion", "fecha_publicacion", "descripcion", "url", "fuente"
    }
    assert oferta["fuente"] == "clinicaalemana.cl"
    assert oferta["url"] == BASE_URL + "/trabajo/6052722-quimico-a-farmaceutico-a"
    assert "Vitacura" in oferta["ubicacion"]
    assert oferta["fecha_publicacion"] == "Hace 3 días"
    assert oferta["descripcion"] == "Se busca Químico/a Farmacéutico/a para farmacia interna de la clínica."


def test_scraper_guarda_lista_de_portales():
    scraper = _make_scraper()
    assert scraper.portales == [
        {"nombre": "clinicaalemana", "base_url": BASE_URL, "fuente": "clinicaalemana.cl"}
    ]
