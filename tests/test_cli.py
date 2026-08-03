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
