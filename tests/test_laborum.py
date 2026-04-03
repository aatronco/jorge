import responses as responses_lib
from pathlib import Path
from unittest.mock import patch
from scrapers.laborum import LaborumScraper

FIXTURE = (Path(__file__).parent / "fixtures" / "laborum_sample.html").read_text(encoding="utf-8")


def test_parse_filtra_rm():
    scraper = LaborumScraper()
    ofertas = scraper._parse_html(FIXTURE)
    assert len(ofertas) == 1
    assert "Recalcine" in ofertas[0]["empresa"]
    assert "Santiago" in ofertas[0]["ubicacion"]


def test_parse_excluye_talca():
    scraper = LaborumScraper()
    ofertas = scraper._parse_html(FIXTURE)
    assert not any("Talca" in o["ubicacion"] for o in ofertas)


def test_parse_estructura_oferta():
    scraper = LaborumScraper()
    ofertas = scraper._parse_html(FIXTURE)
    oferta = ofertas[0]
    assert set(oferta.keys()) == {
        "titulo", "empresa", "ubicacion", "fecha_publicacion", "descripcion", "url", "fuente"
    }
    assert oferta["fuente"] == "laborum.com"
    assert oferta["url"].startswith("https://www.laborum.com")
    assert "2026" in oferta["fecha_publicacion"]


@responses_lib.activate
def test_fetch_hace_request_por_keyword():
    base_url = "https://www.laborum.com/empleos"
    responses_lib.add(responses_lib.GET, base_url, body=FIXTURE, status=200)
    responses_lib.add(responses_lib.GET, base_url, body=FIXTURE, status=200)
    with patch("scrapers.laborum.time.sleep"):
        scraper = LaborumScraper()
        ofertas = scraper.fetch()
    assert len(ofertas) >= 1
    assert all(o["fuente"] == "laborum.com" for o in ofertas)
