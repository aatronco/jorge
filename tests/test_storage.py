import pytest
import storage

OFERTA_1 = {
    "url": "https://a.cl/1", "titulo": "QF", "empresa": "X", "ubicacion": "Santiago",
    "fecha_publicacion": "2026-04-01", "descripcion": "d", "fuente": "test.cl",
}
OFERTA_2 = {
    "url": "https://a.cl/2", "titulo": "QF2", "empresa": "Y", "ubicacion": "Santiago",
    "fecha_publicacion": "2026-04-02", "descripcion": "d2", "fuente": "test.cl",
}


def test_guardar_inserta_nuevas(tmp_path):
    db = tmp_path / "test.db"
    nuevas = storage.guardar([OFERTA_1], db)
    assert nuevas == 1
    filas = storage.listar(db)
    assert len(filas) == 1
    assert filas[0]["estado"] == "nuevo"
    assert filas[0]["titulo"] == "QF"


def test_guardar_no_duplica_por_url(tmp_path):
    db = tmp_path / "test.db"
    storage.guardar([OFERTA_1], db)
    nuevas = storage.guardar([OFERTA_1], db)
    assert nuevas == 0
    assert len(storage.listar(db)) == 1


def test_marcar_no_se_pierde_en_guardar_posterior(tmp_path):
    db = tmp_path / "test.db"
    storage.guardar([OFERTA_1], db)
    assert storage.marcar(db, "https://a.cl/1", "aplicado") is True
    storage.guardar([OFERTA_1], db)  # re-scrapeada, mismo url
    filas = storage.listar(db)
    assert filas[0]["estado"] == "aplicado"


def test_marcar_url_inexistente_retorna_false(tmp_path):
    db = tmp_path / "test.db"
    storage.init_db(db)
    assert storage.marcar(db, "https://no-existe.cl/1", "aplicado") is False


def test_marcar_estado_invalido_lanza_valueerror(tmp_path):
    db = tmp_path / "test.db"
    storage.guardar([OFERTA_1], db)
    with pytest.raises(ValueError):
        storage.marcar(db, "https://a.cl/1", "estado-inventado")


def test_listar_filtra_por_estado(tmp_path):
    db = tmp_path / "test.db"
    storage.guardar([OFERTA_1, OFERTA_2], db)
    storage.marcar(db, "https://a.cl/1", "aplicado")
    nuevas = storage.listar(db, estado="nuevo")
    assert len(nuevas) == 1
    assert nuevas[0]["url"] == "https://a.cl/2"
