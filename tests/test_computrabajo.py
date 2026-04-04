import responses as responses_lib
from pathlib import Path
from unittest.mock import patch
from scrapers.computrabajo import ComputrabajoScraper

FIXTURE = (Path(__file__).parent / "fixtures" / "computrabajo_sample.html").read_text(encoding="utf-8")


def test_parse_filtra_rm():
    scraper = ComputrabajoScraper()
    ofertas = scraper._parse_html(FIXTURE)
    # Fixture tiene 3 cards: 2 Santiago (RM), 1 Concepción (excluida)
    assert len(ofertas) == 2
    assert "Bagó" in ofertas[0]["empresa"]
    assert "Santiago" in ofertas[0]["ubicacion"]


def test_parse_excluye_concepcion():
    scraper = ComputrabajoScraper()
    ofertas = scraper._parse_html(FIXTURE)
    assert not any("Concepción" in o["ubicacion"] for o in ofertas)


def test_parse_estructura_oferta():
    scraper = ComputrabajoScraper()
    ofertas = scraper._parse_html(FIXTURE)
    oferta = ofertas[0]
    assert set(oferta.keys()) == {
        "titulo", "empresa", "ubicacion", "fecha_publicacion", "descripcion", "url", "fuente"
    }
    assert oferta["fuente"] == "computrabajo.cl"
    assert "cl.computrabajo.com" in oferta["url"]
    assert oferta["titulo"] == "QF Aseguramiento de Calidad"


@responses_lib.activate
def test_fetch_hace_request_por_keyword():
    responses_lib.add(responses_lib.GET, "https://cl.computrabajo.com/trabajo-de-qu%C3%ADmico-farmac%C3%A9utico",
                      body=FIXTURE, status=200)
    responses_lib.add(responses_lib.GET, "https://cl.computrabajo.com/trabajo-de-qf",
                      body=FIXTURE, status=200)
    with patch("scrapers.computrabajo.time.sleep"):
        scraper = ComputrabajoScraper()
        ofertas = scraper.fetch()
    assert len(ofertas) >= 1
    assert all(o["fuente"] == "computrabajo.cl" for o in ofertas)
