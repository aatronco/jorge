import json
from unittest.mock import MagicMock

import storage
import cli

OFERTA_1 = {
    "url": "https://a.cl/1", "titulo": "QF", "empresa": "X", "ubicacion": "Santiago",
    "fecha_publicacion": "2026-04-01", "descripcion": "d", "fuente": "test.cl",
}

CV_EJEMPLO = {"basics": {"name": "Jorge", "summary": "original"}, "work": [], "education": [], "skills": []}


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


def test_cv_save_guarda_cv_estructurado(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cv_file = tmp_path / "cv-estructurado.json"
    cv_file.write_text(json.dumps(CV_EJEMPLO), encoding="utf-8")

    exit_code = cli.main(["cv", "save", str(cv_file), "--profile", "arquitecto"])

    assert exit_code == 0
    guardado = json.loads((tmp_path / "data" / "arquitecto-cv.json").read_text(encoding="utf-8"))
    assert guardado == CV_EJEMPLO


def test_cv_save_archivo_inexistente_retorna_error_claro(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    exit_code = cli.main(["cv", "save", "no-existe.json", "--profile", "arquitecto"])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "No se pudo leer" in out
    assert "Traceback" not in out


def test_cv_save_json_invalido_retorna_error_claro(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    cv_file = tmp_path / "roto.json"
    cv_file.write_text("{esto no es json", encoding="utf-8")

    exit_code = cli.main(["cv", "save", str(cv_file), "--profile", "arquitecto"])

    assert exit_code == 1
    assert "No se pudo leer" in capsys.readouterr().out


def test_cv_save_cv_incompleto_retorna_error_claro(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    incompleto = {k: v for k, v in CV_EJEMPLO.items() if k != "work"}
    cv_file = tmp_path / "incompleto.json"
    cv_file.write_text(json.dumps(incompleto), encoding="utf-8")

    exit_code = cli.main(["cv", "save", str(cv_file), "--profile", "arquitecto"])

    assert exit_code == 1
    assert "work" in capsys.readouterr().out
    assert not (tmp_path / "data" / "arquitecto-cv.json").exists()


def test_cv_show_offer_imprime_datos(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    db = tmp_path / "data" / "arquitecto.db"
    storage.guardar([OFERTA_1], db)

    exit_code = cli.main(["cv", "show-offer", "--profile", "arquitecto", "https://a.cl/1"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "QF" in out
    assert "Santiago" in out


def test_cv_show_offer_no_encontrada_retorna_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    storage.init_db(tmp_path / "data" / "arquitecto.db")

    exit_code = cli.main(["cv", "show-offer", "--profile", "arquitecto", "https://no-existe.cl/1"])

    assert exit_code == 1


def test_cv_tailor_sin_cv_guardado_retorna_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fake_render = MagicMock()
    monkeypatch.setattr(cli.cv, "renderizar_cv", fake_render)

    exit_code = cli.main([
        "cv", "tailor", "--profile", "arquitecto", "https://x.cl/1", "--summary", "x",
    ])

    assert exit_code == 1
    fake_render.assert_not_called()


def test_cv_tailor_oferta_no_encontrada_retorna_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cv_path = tmp_path / "data" / "arquitecto-cv.json"
    cv_path.parent.mkdir(parents=True)
    cv_path.write_text(json.dumps(CV_EJEMPLO), encoding="utf-8")
    fake_render = MagicMock()
    monkeypatch.setattr(cli.cv, "renderizar_cv", fake_render)

    exit_code = cli.main([
        "cv", "tailor", "--profile", "arquitecto", "https://no-existe.cl/1", "--summary", "x",
    ])

    assert exit_code == 1
    fake_render.assert_not_called()


def test_cv_tailor_orden_invalido_retorna_error_claro(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    cv_path = tmp_path / "data" / "arquitecto-cv.json"
    cv_path.parent.mkdir(parents=True)
    cv_path.write_text(json.dumps(CV_EJEMPLO), encoding="utf-8")
    db_path = tmp_path / "data" / "arquitecto.db"
    storage.guardar([{**OFERTA_1, "url": "https://x.cl/1"}], db_path)

    exit_code = cli.main([
        "cv", "tailor", "--profile", "arquitecto", "https://x.cl/1",
        "--summary", "x", "--orden-work", "no-es-un-numero",
    ])

    assert exit_code == 1
    assert "orden-work" in capsys.readouterr().out


def test_cv_tailor_flujo_completo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cv_path = tmp_path / "data" / "arquitecto-cv.json"
    cv_path.parent.mkdir(parents=True)
    cv_path.write_text(json.dumps(CV_EJEMPLO), encoding="utf-8")

    db_path = tmp_path / "data" / "arquitecto.db"
    storage.guardar(
        [{"url": "https://x.cl/1", "titulo": "Arquitecto", "empresa": "X", "ubicacion": "Santiago",
          "fecha_publicacion": "", "descripcion": "", "fuente": "test.cl"}],
        db_path,
    )

    fake_render = MagicMock()
    monkeypatch.setattr(cli.cv, "renderizar_cv", fake_render)

    exit_code = cli.main([
        "cv", "tailor", "--profile", "arquitecto", "https://x.cl/1",
        "--summary", "ajustado", "--orden-work", "", "--orden-skills", "",
    ])

    assert exit_code == 0
    fake_render.assert_called_once()
    oferta_id = cli.cv.id_oferta("https://x.cl/1")
    json_guardado = tmp_path / "data" / "arquitecto-tailored" / f"{oferta_id}.json"
    assert json_guardado.exists()
    assert json.loads(json_guardado.read_text())["basics"]["summary"] == "ajustado"
