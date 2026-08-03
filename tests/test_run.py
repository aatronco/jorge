import pytest
from run import consolidar, cargar_perfil, construir_scrapers

OFERTA_SANTIAGO = {
    "titulo": "QF Regente", "empresa": "Farmacia X", "ubicacion": "Santiago",
    "fecha_publicacion": "2026-04-01", "descripcion": "desc",
    "url": "https://a.cl/1", "fuente": "test.cl",
}
OFERTA_CONDES = {
    "titulo": "QF Control Calidad", "empresa": "Lab Y", "ubicacion": "Las Condes, RM",
    "fecha_publicacion": "2026-04-02", "descripcion": "desc2",
    "url": "https://b.cl/2", "fuente": "test2.cl",
}
OFERTA_DUPLICADA = {
    "titulo": "QF Regente", "empresa": "Farmacia X", "ubicacion": "Santiago",
    "fecha_publicacion": "2026-04-01", "descripcion": "desc",
    "url": "https://a.cl/1", "fuente": "test.cl",
}


def test_consolidar_deduplica_por_url():
    resultado = consolidar([[OFERTA_SANTIAGO], [OFERTA_CONDES, OFERTA_DUPLICADA]])
    urls = [o["url"] for o in resultado]
    assert len(urls) == len(set(urls))
    assert len(resultado) == 2


def test_consolidar_listas_vacias():
    assert consolidar([[], []]) == []


def test_cargar_perfil_lee_yaml(tmp_path, monkeypatch):
    perfiles_dir = tmp_path / "profiles"
    perfiles_dir.mkdir()
    (perfiles_dir / "test.yaml").write_text(
        "nombre: test\nkeywords:\n  - Test\nscrapers:\n  - computrabajo\n", encoding="utf-8"
    )
    monkeypatch.setattr("run.PROFILES_DIR", perfiles_dir)
    perfil = cargar_perfil("test")
    assert perfil == {"nombre": "test", "keywords": ["Test"], "scrapers": ["computrabajo"]}


def test_cargar_perfil_inexistente_lanza_filenotfound(tmp_path, monkeypatch):
    monkeypatch.setattr("run.PROFILES_DIR", tmp_path)
    with pytest.raises(FileNotFoundError):
        cargar_perfil("no-existe")


def test_construir_scrapers_instancia_por_nombre():
    perfil = {"keywords": ["Arquitecto"], "scrapers": ["computrabajo", "indeed"]}
    instancias = construir_scrapers(perfil)
    assert len(instancias) == 2
    assert all(i.keywords == ["Arquitecto"] for i in instancias)


def test_construir_scrapers_portal_list_con_config():
    perfil = {
        "keywords": ["QF"],
        "scrapers": [
            {"portal_list": {"portales": [{"nombre": "x", "base_url": "https://x.cl", "fuente": "x.cl"}]}}
        ],
    }
    instancias = construir_scrapers(perfil)
    assert len(instancias) == 1
    assert instancias[0].portales == [{"nombre": "x", "base_url": "https://x.cl", "fuente": "x.cl"}]
