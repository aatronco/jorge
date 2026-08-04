from pathlib import Path
from scrapers.trabajando import TrabajandoScraper

FIXTURE = (Path(__file__).parent / "fixtures" / "trabajando_sample.html").read_text(encoding="utf-8")


def test_parse_filtra_rm():
    scraper = TrabajandoScraper(keywords=["Químico Farmacéutico"])
    ofertas = scraper._parse_html(FIXTURE)
    assert len(ofertas) == 1
    assert "Farmacia Chile" in ofertas[0]["empresa"]
    assert "Santiago" in ofertas[0]["ubicacion"]


def test_parse_excluye_fuera_rm():
    scraper = TrabajandoScraper(keywords=["Químico Farmacéutico"])
    ofertas = scraper._parse_html(FIXTURE)
    ubicaciones = [o["ubicacion"] for o in ofertas]
    assert not any("Valparaíso" in u for u in ubicaciones)


def test_parse_estructura_oferta():
    scraper = TrabajandoScraper(keywords=["Químico Farmacéutico"])
    ofertas = scraper._parse_html(FIXTURE)
    assert len(ofertas) > 0
    oferta = ofertas[0]
    assert set(oferta.keys()) == {
        "titulo", "empresa", "ubicacion", "fecha_publicacion", "descripcion", "url", "fuente"
    }
    assert oferta["fuente"] == "trabajando.cl"
    assert oferta["url"].startswith("https://www.trabajando.cl")
    assert oferta["titulo"] == "Químico Farmacéutico Regente"
    assert oferta["descripcion"] == "Se busca QF regente para farmacia en zona oriente."


def test_fetch_retorna_vacio_sin_botasaurus(monkeypatch):
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "botasaurus.browser" or name.startswith("botasaurus"):
            raise ImportError("no module named botasaurus")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    scraper = TrabajandoScraper(keywords=["Químico Farmacéutico"])
    assert scraper.fetch() == []
