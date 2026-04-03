from pathlib import Path
from scrapers.indeed import IndeedScraper

FIXTURE = (Path(__file__).parent / "fixtures" / "indeed_sample.html").read_text(encoding="utf-8")


def test_parse_filtra_rm():
    scraper = IndeedScraper()
    ofertas = scraper._parse_html(FIXTURE)
    assert len(ofertas) == 1
    assert "Maver" in ofertas[0]["empresa"]
    assert "Santiago" in ofertas[0]["ubicacion"]


def test_parse_excluye_vina():
    scraper = IndeedScraper()
    ofertas = scraper._parse_html(FIXTURE)
    assert not any("Viña" in o["ubicacion"] for o in ofertas)


def test_parse_estructura_oferta():
    scraper = IndeedScraper()
    ofertas = scraper._parse_html(FIXTURE)
    oferta = ofertas[0]
    assert set(oferta.keys()) == {
        "titulo", "empresa", "ubicacion", "fecha_publicacion", "descripcion", "url", "fuente"
    }
    assert oferta["fuente"] == "indeed.cl"
    assert "cl.indeed.com" in oferta["url"]
    assert oferta["titulo"] == "Químico Farmacéutico Senior"
