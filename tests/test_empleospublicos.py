from pathlib import Path
from unittest.mock import patch
import responses as responses_lib
from scrapers.empleospublicos import EmpleosPublicosScraper

FIXTURE = (Path(__file__).parent / "fixtures" / "empleospublicos_sample.html").read_text(encoding="utf-8")


def test_parse_filtra_qf():
    scraper = EmpleosPublicosScraper()
    ofertas = scraper._parse_html(FIXTURE)
    # fixture: 2 cards con "químico farmacéutico" en título, 1 card "médico cirujano" excluida
    assert len(ofertas) == 2
    titulos = [o["titulo"].lower() for o in ofertas]
    assert all("químico" in t for t in titulos)


def test_parse_excluye_no_qf():
    scraper = EmpleosPublicosScraper()
    ofertas = scraper._parse_html(FIXTURE)
    titulos = [o["titulo"] for o in ofertas]
    assert not any("MÉDICO CIRUJANO" in t for t in titulos)


def test_parse_estructura_oferta():
    scraper = EmpleosPublicosScraper()
    ofertas = scraper._parse_html(FIXTURE)
    assert len(ofertas) > 0
    oferta = ofertas[0]
    assert set(oferta.keys()) == {
        "titulo", "empresa", "ubicacion", "fecha_publicacion", "descripcion", "url", "fuente"
    }
    assert oferta["fuente"] == "empleospublicos.cl"
    assert oferta["ubicacion"] == ""  # intencionalmente vacío — incluye empleos de todo Chile
    assert "La Florida" in oferta["empresa"]
    assert oferta["url"].startswith("https://www.empleospublicos.cl/pub/convocatorias/")
    assert "2026" in oferta["fecha_publicacion"]


@responses_lib.activate
def test_fetch_hace_request():
    url1 = "https://www.empleospublicos.cl/pub/convocatorias/convocatorias.aspx?busqueda=qu%C3%ADmico+farmac%C3%A9utico"
    url2 = "https://www.empleospublicos.cl/pub/convocatorias/convocatorias.aspx?busqueda=farmac%C3%A9utico+regente"
    responses_lib.add(responses_lib.GET, url1, body=FIXTURE, status=200)
    responses_lib.add(responses_lib.GET, url2, body=FIXTURE, status=200)
    with patch("scrapers.empleospublicos.time.sleep"):
        scraper = EmpleosPublicosScraper()
        ofertas = scraper.fetch()
    assert isinstance(ofertas, list)
    assert all(o["fuente"] == "empleospublicos.cl" for o in ofertas)
