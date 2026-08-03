from pathlib import Path

import pytest

import run

PROFILES_DIR = Path(__file__).parent.parent / "profiles"


@pytest.mark.parametrize("nombre", [f.stem for f in PROFILES_DIR.glob("*.yaml")])
def test_perfil_resuelve_contra_registry(nombre):
    perfil = run.cargar_perfil(nombre)
    instancias = run.construir_scrapers(perfil)
    assert instancias
    assert perfil["keywords"]
    assert perfil["nombre"] == nombre


def test_qf_portal_list_keywords_matchean_titulo_real():
    """Regresión: profiles/qf.yaml debe incluir keywords que matcheen
    variantes reales de título como 'Químico/a Farmacéutico/a', no solo
    frases completas — de lo contrario portal_list.py filtra todo."""
    perfil = run.cargar_perfil("qf")
    titulo_real = "Químico/a Farmacéutico/a"
    assert any(kw.lower() in titulo_real.lower() for kw in perfil["keywords"])
