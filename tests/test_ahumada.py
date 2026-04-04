from pathlib import Path
import responses as responses_lib
from scrapers.ahumada import AhumadaScraper

FIXTURE = (Path(__file__).parent / "fixtures" / "ahumada_sample.html").read_text(encoding="utf-8")


def test_parse_filtra_rm():
    scraper = AhumadaScraper()
    ofertas = scraper._parse_html(FIXTURE)
    # fixture: 1 QF en Santiago (RM), 1 Auxiliar RM excluido, 1 QF Parral excluido
    assert len(ofertas) == 1
    assert "Santiago" in ofertas[0]["ubicacion"]


def test_parse_excluye_fuera_rm():
    scraper = AhumadaScraper()
    ofertas = scraper._parse_html(FIXTURE)
    assert not any("Parral" in o["ubicacion"] for o in ofertas)


def test_parse_filtra_qf():
    scraper = AhumadaScraper()
    ofertas = scraper._parse_html(FIXTURE)
    # "Auxiliar de Farmacia" debe excluirse aunque sea RM
    titulos = [o["titulo"].lower() for o in ofertas]
    assert not any("auxiliar" in t for t in titulos)
    assert all("químico" in t or "farmacéutico" in t or "regente" in t for t in titulos)


def test_parse_estructura_oferta():
    scraper = AhumadaScraper()
    ofertas = scraper._parse_html(FIXTURE)
    assert len(ofertas) > 0
    oferta = ofertas[0]
    assert set(oferta.keys()) == {
        "titulo", "empresa", "ubicacion", "fecha_publicacion", "descripcion", "url", "fuente"
    }
    assert oferta["fuente"] == "farmaciasahumada.cl"
    assert oferta["empresa"] == "Farmacias Ahumada"
    assert oferta["url"].startswith("https://farmaciasahumada.buk.cl/s/")
    assert "Regente" in oferta["titulo"]


@responses_lib.activate
def test_fetch_hace_request():
    url = "https://farmaciasahumada.buk.cl/trabaja-con-nosotros"
    responses_lib.add(responses_lib.GET, url, body=FIXTURE, status=200)
    scraper = AhumadaScraper()
    ofertas = scraper.fetch()
    assert isinstance(ofertas, list)
    assert all(o["fuente"] == "farmaciasahumada.cl" for o in ofertas)
