import pandas as pd
from pathlib import Path
from run import consolidar, guardar_csv, COLUMNAS

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


def test_guardar_csv_crea_archivo(tmp_path):
    csv_path = tmp_path / "test.csv"
    guardar_csv([OFERTA_SANTIAGO, OFERTA_CONDES], csv_path)
    assert csv_path.exists()
    df = pd.read_csv(csv_path)
    assert list(df.columns) == COLUMNAS
    assert len(df) == 2


def test_guardar_csv_acumula_sin_duplicar(tmp_path):
    csv_path = tmp_path / "test.csv"
    guardar_csv([OFERTA_SANTIAGO], csv_path)
    guardar_csv([OFERTA_CONDES], csv_path)
    df = pd.read_csv(csv_path)
    assert len(df) == 2


def test_guardar_csv_no_duplica_misma_url(tmp_path):
    csv_path = tmp_path / "test.csv"
    guardar_csv([OFERTA_SANTIAGO], csv_path)
    guardar_csv([OFERTA_SANTIAGO], csv_path)
    df = pd.read_csv(csv_path)
    assert len(df) == 1


def test_guardar_csv_columnas_ordenadas(tmp_path):
    csv_path = tmp_path / "test.csv"
    guardar_csv([OFERTA_SANTIAGO], csv_path)
    df = pd.read_csv(csv_path)
    assert list(df.columns) == COLUMNAS
