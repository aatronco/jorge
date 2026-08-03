# tests/test_base.py
import pytest
from scrapers.base import BaseScraper, is_region_metropolitana


def test_rm_keywords_positivos():
    assert is_region_metropolitana("Santiago") is True
    assert is_region_metropolitana("Providencia, Región Metropolitana") is True
    assert is_region_metropolitana("Las Condes, RM") is True
    assert is_region_metropolitana("Puente Alto") is True
    assert is_region_metropolitana("Maipú") is True
    assert is_region_metropolitana("San Bernardo") is True


def test_rm_keywords_negativos():
    assert is_region_metropolitana("Valparaíso") is False
    assert is_region_metropolitana("Concepción") is False
    assert is_region_metropolitana("Antofagasta") is False
    assert is_region_metropolitana("Temuco") is False
    assert is_region_metropolitana("La Serena") is False


def test_rm_sin_ubicacion_incluye():
    assert is_region_metropolitana("") is True
    assert is_region_metropolitana(None) is True


def test_base_scraper_es_abstracta():
    with pytest.raises(TypeError):
        BaseScraper(keywords=["test"])


def test_make_oferta_normaliza_none():
    class Concreto(BaseScraper):
        def fetch(self):
            return []

    scraper = Concreto(keywords=["test"])
    oferta = scraper._make_oferta(None, None, None, None, None, None, "test")
    for k, v in oferta.items():
        if k != "fuente":
            assert v == "", f"Campo '{k}' debería ser '' pero es {v!r}"
    assert oferta["fuente"] == "test"


def test_make_oferta_normaliza_fuente_none():
    class Concreto(BaseScraper):
        def fetch(self):
            return []
    scraper = Concreto(keywords=["test"])
    oferta = scraper._make_oferta(None, None, None, None, None, None, None)
    assert oferta["fuente"] == ""


def test_make_oferta_estructura_completa():
    class Concreto(BaseScraper):
        def fetch(self):
            return []

    scraper = Concreto(keywords=["test"])
    oferta = scraper._make_oferta("QF", "Lab", "Santiago", "2026-04-01", "desc", "https://x.cl", "fuente")
    assert set(oferta.keys()) == {
        "titulo", "empresa", "ubicacion", "fecha_publicacion", "descripcion", "url", "fuente"
    }


def test_keyword_search_scraper_guarda_keywords():
    from scrapers.base import KeywordSearchScraper

    class Concreto(KeywordSearchScraper):
        def fetch(self):
            return []

    scraper = Concreto(keywords=["Arquitecto", "Arquitectura"])
    assert scraper.keywords == ["Arquitecto", "Arquitectura"]


def test_portal_list_scraper_guarda_portales():
    from scrapers.base import PortalListScraper

    class Concreto(PortalListScraper):
        def fetch(self):
            return []

    portales = [{"nombre": "x", "base_url": "https://x.cl", "fuente": "x.cl"}]
    scraper = Concreto(keywords=["QF"], portales=portales)
    assert scraper.portales == portales
    assert scraper.keywords == ["QF"]
