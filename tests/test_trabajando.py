from pathlib import Path
from scrapers.trabajando import TrabajandoScraper
import responses as responses_lib

FIXTURE = (Path(__file__).parent / "fixtures" / "trabajando_sample.html").read_text(encoding="utf-8")


def test_parse_filtra_rm():
    scraper = TrabajandoScraper()
    ofertas = scraper._parse_html(FIXTURE)
    assert len(ofertas) == 1
    assert "Farmacia Chile" in ofertas[0]["empresa"]
    assert "Santiago" in ofertas[0]["ubicacion"]


def test_parse_excluye_fuera_rm():
    scraper = TrabajandoScraper()
    ofertas = scraper._parse_html(FIXTURE)
    ubicaciones = [o["ubicacion"] for o in ofertas]
    assert not any("Valparaíso" in u for u in ubicaciones)


def test_parse_estructura_oferta():
    scraper = TrabajandoScraper()
    ofertas = scraper._parse_html(FIXTURE)
    assert len(ofertas) > 0
    oferta = ofertas[0]
    assert set(oferta.keys()) == {
        "titulo", "empresa", "ubicacion", "fecha_publicacion", "descripcion", "url", "fuente"
    }
    assert oferta["fuente"] == "trabajando.cl"
    assert oferta["url"].startswith("https://www.trabajando.cl")
    assert oferta["titulo"] == "Químico Farmacéutico Regente"


@responses_lib.activate
def test_fetch_hace_request_por_keyword():
    from unittest.mock import patch
    # Mock both keyword searches
    responses_lib.add(responses_lib.GET, "https://www.trabajando.cl/trabajo/buscar",
                      body=FIXTURE, status=200)
    responses_lib.add(responses_lib.GET, "https://www.trabajando.cl/trabajo/buscar",
                      body=FIXTURE, status=200)

    with patch("scrapers.trabajando.time.sleep"):  # skip sleep in tests
        scraper = TrabajandoScraper()
        ofertas = scraper.fetch()

    assert len(ofertas) >= 1
    assert all(o["fuente"] == "trabajando.cl" for o in ofertas)
