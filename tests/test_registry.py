import pytest
from scrapers import registry


def test_register_and_get():
    @registry.register("dummy_test_scraper")
    class Dummy:
        pass

    assert registry.get("dummy_test_scraper") is Dummy


def test_get_unregistered_raises_keyerror():
    with pytest.raises(KeyError):
        registry.get("no_existe_este_scraper")


def test_all_names_incluye_registrados():
    @registry.register("otro_dummy")
    class Otro:
        pass

    assert "otro_dummy" in registry.all_names()
