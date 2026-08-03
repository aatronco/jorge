import copy
import json
from pathlib import Path
from unittest.mock import MagicMock

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

OFERTA_EJEMPLO = {
    "titulo": "Arquitecto de Aplicaciones", "empresa": "AFP Habitat", "ubicacion": "Providencia",
    "descripcion": "Buscamos arquitecto senior con experiencia en sistemas de información.",
    "url": "https://x.cl/1", "fuente": "laborum.cl",
}


def _mock_tool_use_response(payload: dict):
    block = MagicMock()
    block.type = "tool_use"
    block.input = payload
    response = MagicMock()
    response.content = [block]
    return response


def test_importar_cv_llama_api_y_guarda(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _mock_tool_use_response(CV_EJEMPLO)
    monkeypatch.setattr(cv, "_client", lambda: fake_client)

    resultado = cv.importar_cv("Jorge Pérez, arquitecto...", "arquitecto")

    assert resultado == CV_EJEMPLO
    guardado = json.loads((tmp_path / "data" / "arquitecto-cv.json").read_text(encoding="utf-8"))
    assert guardado == CV_EJEMPLO

    call_kwargs = fake_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == cv.MODEL
    assert call_kwargs["tool_choice"]["name"] == call_kwargs["tools"][0]["name"]


def test_tailorear_cv_no_muta_cv_base(monkeypatch):
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _mock_tool_use_response(
        {"orden_work": [1, 0], "orden_skills": [1, 0], "summary": "Resumen ajustado a esta oferta."}
    )
    monkeypatch.setattr(cv, "_client", lambda: fake_client)

    original = copy.deepcopy(CV_EJEMPLO)
    resultado = cv.tailorear_cv(CV_EJEMPLO, OFERTA_EJEMPLO)

    assert CV_EJEMPLO == original  # cv_base intacto
    assert resultado is not CV_EJEMPLO


def test_tailorear_cv_reordena_y_preserva_cantidad(monkeypatch):
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _mock_tool_use_response(
        {"orden_work": [1, 0], "orden_skills": [1, 0], "summary": "Resumen ajustado a esta oferta."}
    )
    monkeypatch.setattr(cv, "_client", lambda: fake_client)

    resultado = cv.tailorear_cv(CV_EJEMPLO, OFERTA_EJEMPLO)

    assert len(resultado["work"]) == len(CV_EJEMPLO["work"])
    assert len(resultado["skills"]) == len(CV_EJEMPLO["skills"])
    assert resultado["work"][0]["name"] == "Estudio B"  # índice 1 primero
    assert resultado["skills"][0]["name"] == "Revit"  # índice 1 primero
    assert resultado["basics"]["summary"] == "Resumen ajustado a esta oferta."


def test_tailorear_cv_incluye_datos_de_la_oferta_en_el_prompt(monkeypatch):
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _mock_tool_use_response(
        {"orden_work": [], "orden_skills": [], "summary": "x"}
    )
    monkeypatch.setattr(cv, "_client", lambda: fake_client)

    cv.tailorear_cv(CV_EJEMPLO, OFERTA_EJEMPLO)

    prompt = fake_client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "Arquitecto de Aplicaciones" in prompt
    assert "sistemas de información" in prompt
