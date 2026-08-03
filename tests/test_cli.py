from unittest.mock import MagicMock

import storage
import cli

OFERTA_1 = {
    "url": "https://a.cl/1", "titulo": "QF", "empresa": "X", "ubicacion": "Santiago",
    "fecha_publicacion": "2026-04-01", "descripcion": "d", "fuente": "test.cl",
}


def test_mark_url_existente_actualiza_estado(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db = tmp_path / "data" / "qf.db"
    storage.guardar([OFERTA_1], db)
    exit_code = cli.main(["mark", "--profile", "qf", "https://a.cl/1", "aplicado", "--no-anim"])
    assert exit_code == 0
    assert storage.listar(db)[0]["estado"] == "aplicado"


def test_mark_url_inexistente_retorna_exit_code_1(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db = tmp_path / "data" / "qf.db"
    storage.init_db(db)
    exit_code = cli.main(["mark", "--profile", "qf", "https://no.cl/1", "aplicado", "--no-anim"])
    assert exit_code == 1


def test_mark_estado_invalido_rechazado_por_argparse():
    import pytest
    with pytest.raises(SystemExit):
        cli.main(["mark", "--profile", "qf", "https://a.cl/1", "estado-inventado", "--no-anim"])


def test_list_imprime_titulo_de_oferta(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    db = tmp_path / "data" / "qf.db"
    storage.guardar([OFERTA_1], db)
    exit_code = cli.main(["list", "--profile", "qf", "--no-anim"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "QF" in out


def test_list_filtra_por_status(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    db = tmp_path / "data" / "qf.db"
    otra = {**OFERTA_1, "url": "https://a.cl/2", "titulo": "OtraOferta"}
    storage.guardar([OFERTA_1, otra], db)
    storage.marcar(db, "https://a.cl/1", "aplicado")
    cli.main(["list", "--profile", "qf", "--status", "nuevo", "--no-anim"])
    out = capsys.readouterr().out
    assert "OtraOferta" in out
    assert "QF" not in out.replace("OtraOferta", "")


def test_cv_import_llama_a_cv_importar_cv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fake_importar = MagicMock(return_value={"basics": {"summary": "x"}})
    monkeypatch.setattr(cli.cv, "importar_cv", fake_importar)

    cv_file = tmp_path / "mi-cv.txt"
    cv_file.write_text("Jorge Pérez, arquitecto...", encoding="utf-8")

    exit_code = cli.main(["cv", "import", str(cv_file), "--profile", "arquitecto"])

    assert exit_code == 0
    fake_importar.assert_called_once()
    args, kwargs = fake_importar.call_args
    assert args[0] == "Jorge Pérez, arquitecto..."
    assert args[1] == "arquitecto"


def test_cv_import_archivo_inexistente_retorna_error_claro(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    exit_code = cli.main(["cv", "import", "no-existe.txt", "--profile", "arquitecto"])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "No se pudo leer" in out
    assert "Traceback" not in out


def test_cv_tailor_sin_cv_importado_retorna_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tailorear_mock = MagicMock()
    monkeypatch.setattr(cli.cv, "tailorear_cv", tailorear_mock)

    exit_code = cli.main(["cv", "tailor", "--profile", "arquitecto", "https://x.cl/1"])

    assert exit_code == 1
    tailorear_mock.assert_not_called()


def test_cv_tailor_oferta_no_encontrada_retorna_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cv_path = tmp_path / "data" / "arquitecto-cv.json"
    cv_path.parent.mkdir(parents=True)
    cv_path.write_text('{"basics": {}, "work": [], "education": [], "skills": []}', encoding="utf-8")
    tailorear_mock = MagicMock()
    monkeypatch.setattr(cli.cv, "tailorear_cv", tailorear_mock)

    exit_code = cli.main(["cv", "tailor", "--profile", "arquitecto", "https://no-existe.cl/1"])

    assert exit_code == 1
    tailorear_mock.assert_not_called()


def test_cv_import_error_de_api_retorna_error_claro(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli.cv, "importar_cv", MagicMock(side_effect=RuntimeError("401 unauthorized")))
    cv_file = tmp_path / "mi-cv.txt"
    cv_file.write_text("texto", encoding="utf-8")

    exit_code = cli.main(["cv", "import", str(cv_file), "--profile", "arquitecto"])

    assert exit_code == 1
    assert "API" in capsys.readouterr().out


def test_cv_tailor_flujo_completo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cv_base = {"basics": {"summary": "original"}, "work": [], "education": [], "skills": []}
    cv_path = tmp_path / "data" / "arquitecto-cv.json"
    cv_path.parent.mkdir(parents=True)
    import json
    cv_path.write_text(json.dumps(cv_base), encoding="utf-8")

    db_path = tmp_path / "data" / "arquitecto.db"
    storage.guardar(
        [{"url": "https://x.cl/1", "titulo": "Arquitecto", "empresa": "X", "ubicacion": "Santiago",
          "fecha_publicacion": "", "descripcion": "", "fuente": "test.cl"}],
        db_path,
    )

    tailored = {"basics": {"summary": "ajustado"}, "work": [], "education": [], "skills": []}
    monkeypatch.setattr(cli.cv, "tailorear_cv", MagicMock(return_value=tailored))
    fake_render = MagicMock()
    monkeypatch.setattr(cli.cv, "renderizar_cv", fake_render)

    exit_code = cli.main(["cv", "tailor", "--profile", "arquitecto", "https://x.cl/1"])

    assert exit_code == 0
    fake_render.assert_called_once()
    oferta_id = cli.cv.id_oferta("https://x.cl/1")
    json_guardado = tmp_path / "data" / "arquitecto-tailored" / f"{oferta_id}.json"
    assert json_guardado.exists()
    assert json.loads(json_guardado.read_text())["basics"]["summary"] == "ajustado"
