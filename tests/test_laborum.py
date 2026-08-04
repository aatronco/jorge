from pathlib import Path
from scrapers.laborum import LaborumScraper

FIXTURE = (Path(__file__).parent / "fixtures" / "laborum_sample.html").read_text(encoding="utf-8")


def test_parse_filtra_rm():
    scraper = LaborumScraper(keywords=["Químico Farmacéutico"])
    ofertas = scraper._parse_html(FIXTURE)
    assert len(ofertas) == 1
    assert "Recalcine" in ofertas[0]["empresa"]
    assert "Santiago" in ofertas[0]["ubicacion"]


def test_parse_excluye_talca():
    scraper = LaborumScraper(keywords=["Químico Farmacéutico"])
    ofertas = scraper._parse_html(FIXTURE)
    assert not any("Talca" in o["ubicacion"] for o in ofertas)


def test_parse_estructura_oferta():
    scraper = LaborumScraper(keywords=["Químico Farmacéutico"])
    ofertas = scraper._parse_html(FIXTURE)
    oferta = ofertas[0]
    assert set(oferta.keys()) == {
        "titulo", "empresa", "ubicacion", "fecha_publicacion", "descripcion", "url", "fuente"
    }
    assert oferta["fuente"] == "laborum.cl"
    assert oferta["url"].startswith("https://www.laborum.cl")
    assert oferta["titulo"] == "Químico Farmacéutico"
    assert oferta["fecha_publicacion"] == "Publicado hace 2 horas"
    assert oferta["descripcion"] == "Buscamos QF para área de producción en planta Santiago."


def test_fetch_retorna_vacio_sin_botasaurus(monkeypatch):
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "botasaurus.browser" or name.startswith("botasaurus"):
            raise ImportError("no module named botasaurus")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    scraper = LaborumScraper(keywords=["Químico Farmacéutico"])
    assert scraper.fetch() == []
