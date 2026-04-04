from pathlib import Path
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


def test_fetch_retorna_vacio_sitio_bloqueado(capsys):
    # laborum.com bloquea automatización; fetch() retorna [] con mensaje
    scraper = LaborumScraper()
    ofertas = scraper.fetch()
    assert ofertas == []
    captured = capsys.readouterr()
    assert "bloquea" in captured.out.lower() or "skip" in captured.out.lower()
