import copy
import json
import subprocess
from pathlib import Path

import pytest

import cv


def test_aplicar_orden_reordena_sin_perder_items():
    items = ["a", "b", "c"]
    resultado = cv._aplicar_orden(items, [2, 0, 1])
    assert resultado == ["c", "a", "b"]


def test_aplicar_orden_agrega_faltantes_al_final():
    items = ["a", "b", "c"]
    resultado = cv._aplicar_orden(items, [1])
    assert resultado == ["b", "a", "c"]


def test_aplicar_orden_ignora_indices_invalidos():
    items = ["a", "b"]
    resultado = cv._aplicar_orden(items, [5, 0, -1])
    assert resultado == ["a", "b"]


def test_aplicar_orden_ignora_duplicados():
    items = ["a", "b", "c"]
    resultado = cv._aplicar_orden(items, [1, 1, 0])
    assert resultado == ["b", "a", "c"]


def test_aplicar_orden_nunca_cambia_la_cantidad():
    items = ["a", "b", "c", "d"]
    for orden in ([], [3], [3, 2, 1, 0], [0, 0, 0]):
        assert len(cv._aplicar_orden(items, orden)) == len(items)


CV_EJEMPLO = {
    "basics": {"name": "Jorge Pérez", "label": "Arquitecto", "summary": "Arquitecto con 10 años de experiencia."},
    "work": [
        {"name": "Estudio A", "position": "Arquitecto Junior", "startDate": "2016", "endDate": "2019"},
        {"name": "Estudio B", "position": "Arquitecto Senior", "startDate": "2019", "endDate": "2026"},
    ],
    "education": [{"institution": "Universidad de Chile", "area": "Arquitectura", "studyType": "Licenciatura"}],
    "skills": [{"name": "AutoCAD"}, {"name": "Revit"}],
}


def test_guardar_cv_escribe_archivo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    cv.guardar_cv(CV_EJEMPLO, "arquitecto")

    guardado = json.loads((tmp_path / "data" / "arquitecto-cv.json").read_text(encoding="utf-8"))
    assert guardado == CV_EJEMPLO


def test_guardar_cv_rechaza_cv_incompleto(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    incompleto = {k: v for k, v in CV_EJEMPLO.items() if k != "work"}

    with pytest.raises(ValueError, match="work"):
        cv.guardar_cv(incompleto, "arquitecto")

    assert not (tmp_path / "data" / "arquitecto-cv.json").exists()


def test_aplicar_tailoring_no_muta_cv_base():
    original = copy.deepcopy(CV_EJEMPLO)

    resultado = cv.aplicar_tailoring(CV_EJEMPLO, [1, 0], [1, 0], "Resumen ajustado a esta oferta.")

    assert CV_EJEMPLO == original  # cv_base intacto
    assert resultado is not CV_EJEMPLO


def test_aplicar_tailoring_no_comparte_referencias_anidadas():
    resultado = cv.aplicar_tailoring(CV_EJEMPLO, [1, 0], [1, 0], "Resumen ajustado a esta oferta.")

    # Mutar el resultado no debe afectar CV_EJEMPLO — si compartieran referencias
    # anidadas (ej. una copia superficial), esta mutación se propagaría.
    resultado["work"][0]["position"] = "MUTATED"
    resultado["basics"]["summary"] = "MUTATED"
    assert CV_EJEMPLO["work"][0]["position"] != "MUTATED"
    assert CV_EJEMPLO["work"][1]["position"] != "MUTATED"
    assert CV_EJEMPLO["basics"]["summary"] != "MUTATED"


def test_aplicar_tailoring_reordena_y_preserva_cantidad():
    resultado = cv.aplicar_tailoring(CV_EJEMPLO, [1, 0], [1, 0], "Resumen ajustado a esta oferta.")

    assert len(resultado["work"]) == len(CV_EJEMPLO["work"])
    assert len(resultado["skills"]) == len(CV_EJEMPLO["skills"])
    assert resultado["work"][0]["name"] == "Estudio B"  # índice 1 primero
    assert resultado["skills"][0]["name"] == "Revit"  # índice 1 primero
    assert resultado["basics"]["summary"] == "Resumen ajustado a esta oferta."


def test_aplicar_tailoring_ordenes_vacios_mantiene_orden_original():
    resultado = cv.aplicar_tailoring(CV_EJEMPLO, [], [], "x")

    assert [w["name"] for w in resultado["work"]] == [w["name"] for w in CV_EJEMPLO["work"]]
    assert [s["name"] for s in resultado["skills"]] == [s["name"] for s in CV_EJEMPLO["skills"]]


def test_id_oferta_es_estable_y_corto():
    a = cv.id_oferta("https://x.cl/empleo/1")
    b = cv.id_oferta("https://x.cl/empleo/1")
    c = cv.id_oferta("https://x.cl/empleo/2")
    assert a == b
    assert a != c
    assert len(a) == 12


def test_renderizar_cv_llama_resumed_con_argumentos_correctos(tmp_path, monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    json_path = tmp_path / "cv.json"
    output_path = tmp_path / "sub" / "cv.pdf"

    cv.renderizar_cv(json_path, output_path)

    assert len(calls) == 1
    args = calls[0]
    assert args[:2] == ["resumed", "export"]
    assert str(json_path) in args
    assert str(output_path) in args
    assert "-t" in args and "jsonresume-theme-even" in args
    assert output_path.parent.exists()  # se crea el directorio destino


def test_renderizar_cv_error_claro_si_resumed_no_instalado(tmp_path, monkeypatch):
    def fake_run(args, **kwargs):
        raise FileNotFoundError("no such file: resumed")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="npm install -g resumed jsonresume-theme-even puppeteer"):
        cv.renderizar_cv(tmp_path / "cv.json", tmp_path / "cv.pdf")


def test_renderizar_cv_error_si_resumed_falla(tmp_path, monkeypatch):
    def fake_run(args, **kwargs):
        raise subprocess.CalledProcessError(1, args, stderr=b"theme not found")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="theme not found"):
        cv.renderizar_cv(tmp_path / "cv.json", tmp_path / "cv.pdf")
