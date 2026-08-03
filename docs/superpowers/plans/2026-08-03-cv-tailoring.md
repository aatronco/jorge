# CV Tailoring Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a CV-tailoring pipeline to `jorge`: structure a CV once via the Anthropic API into the JSON Resume schema, then per scraped job posting generate a tailored PDF (reordered experience/skills + a new summary, never inventing content) via the `resumed` CLI, exposed as new `cli.py` subcommands.

**Architecture:** New standalone module `cv.py` with three functions (`importar_cv`, `tailorear_cv`, `renderizar_cv`) plus a pure reordering helper (`_aplicar_orden`). Both Anthropic calls go through one small `_tool_call` wrapper using forced tool-use for structured output, so tests mock one seam. `cli.py` gains a `cv` subcommand group (`cv import`, `cv tailor`) that wires `cv.py` to the existing `storage.py`. `storage.py` gains one new read function, `obtener_por_url`, so `cv tailor` can look up a single saved offer.

**Tech Stack:** Python 3.12, `anthropic` (Claude API, forced tool-use for structured JSON output), stdlib `subprocess` (shells out to the Node.js `resumed` CLI), stdlib `hashlib` (stable short IDs from offer URLs), `pytest` + `unittest.mock` (all Anthropic/subprocess calls mocked in tests — no real API spend, no real Node.js invocation in the suite).

## Global Constraints

- `tailorear_cv` must never mutate its `cv_base` argument, and the tailored output must contain exactly the same `work[]`/`skills[]` entries as the input — reordered only, never added, removed, or rewritten. This is the core safety property of the whole feature (per spec: "cero riesgo de que la IA invente algo que no pasó").
- All generated artifacts (`data/<perfil>-cv.json`, `data/<perfil>-tailored/*.json`, `data/<perfil>-tailored/*.pdf`) live under `data/`, already gitignored — never write generated CVs/resumes anywhere else in the repo tree.
- `resumed` (Node.js CLI) is a system prerequisite, not a pip package. Its absence must produce a clear `RuntimeError` with the exact install command (`npm install -g resumed jsonresume-theme-even`), never a raw traceback.
- No test in this plan may make a real network call to the Anthropic API or a real `resumed`/Node.js subprocess call — every task's tests mock these seams.
- Model id: `claude-sonnet-5` (current Sonnet 5 model id).

---

### Task 1: `cv.py` scaffolding — schemas, `_tool_call` wrapper, `_aplicar_orden` helper

**Files:**
- Create: `cv.py`
- Test: `tests/test_cv.py`
- Modify: `requirements-scraper.txt`

**Interfaces:**
- Produces: `MODEL: str`, `CV_SCHEMA: dict`, `TAILOR_SCHEMA: dict`, `_client() -> anthropic.Anthropic`, `_tool_call(client, tool_name: str, tool_description: str, schema: dict, prompt: str) -> dict`, `_aplicar_orden(items: list, orden: list[int]) -> list`.

This task lays the foundation later tasks build on. `_aplicar_orden` is the correctness-critical piece (Global Constraints) — it's tested in isolation, with no Anthropic involvement at all.

- [ ] **Step 1: Add the `anthropic` dependency**

Edit `requirements-scraper.txt`, adding this line (anywhere after the existing entries):

```
anthropic==0.39.0
```

- [ ] **Step 2: Write the failing test for `_aplicar_orden`**

```python
# tests/test_cv.py
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_cv.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cv'` (or `AttributeError` once the empty file exists).

- [ ] **Step 4: Write minimal implementation**

```python
# cv.py
import anthropic

MODEL = "claude-sonnet-5"

CV_SCHEMA = {
    "type": "object",
    "properties": {
        "basics": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "label": {"type": "string"},
                "email": {"type": "string"},
                "phone": {"type": "string"},
                "summary": {"type": "string"},
            },
            "required": ["name", "summary"],
        },
        "work": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "position": {"type": "string"},
                    "startDate": {"type": "string"},
                    "endDate": {"type": "string"},
                    "summary": {"type": "string"},
                    "highlights": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["name", "position"],
            },
        },
        "education": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "institution": {"type": "string"},
                    "area": {"type": "string"},
                    "studyType": {"type": "string"},
                    "startDate": {"type": "string"},
                    "endDate": {"type": "string"},
                },
                "required": ["institution"],
            },
        },
        "skills": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "level": {"type": "string"},
                    "keywords": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["name"],
            },
        },
    },
    "required": ["basics", "work", "education", "skills"],
}

TAILOR_SCHEMA = {
    "type": "object",
    "properties": {
        "orden_work": {
            "type": "array",
            "items": {"type": "integer"},
            "description": "Índices de cv_base['work'], en el orden en que deberían aparecer (más relevante primero).",
        },
        "orden_skills": {
            "type": "array",
            "items": {"type": "integer"},
            "description": "Índices de cv_base['skills'], en el orden en que deberían aparecer (más relevante primero).",
        },
        "summary": {
            "type": "string",
            "description": "Nuevo resumen profesional (basics.summary) adaptado a esta oferta específica.",
        },
    },
    "required": ["orden_work", "orden_skills", "summary"],
}


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def _tool_call(client, tool_name: str, tool_description: str, schema: dict, prompt: str) -> dict:
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        tools=[{"name": tool_name, "description": tool_description, "input_schema": schema}],
        tool_choice={"type": "tool", "name": tool_name},
        messages=[{"role": "user", "content": prompt}],
    )
    for block in response.content:
        if block.type == "tool_use":
            return block.input
    raise ValueError("Claude no devolvió una respuesta con tool_use")


def _aplicar_orden(items: list, orden: list) -> list:
    """Reordena `items` según `orden` (lista de índices). Nunca cambia la
    cantidad de elementos: índices inválidos/duplicados se ignoran, y los
    elementos no mencionados en `orden` se agregan al final en su orden
    original."""
    vistos = set()
    resultado = []
    for i in orden:
        if isinstance(i, int) and 0 <= i < len(items) and i not in vistos:
            vistos.add(i)
            resultado.append(items[i])
    for i in range(len(items)):
        if i not in vistos:
            resultado.append(items[i])
    return resultado
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_cv.py -v`
Expected: PASS (5 passed)

- [ ] **Step 6: Commit**

```bash
git add cv.py tests/test_cv.py requirements-scraper.txt
git commit -m "feat: add cv.py scaffolding (schemas, tool-call wrapper, reorder helper)"
```

---

### Task 2: `importar_cv`

**Files:**
- Modify: `cv.py`
- Modify: `tests/test_cv.py`

**Interfaces:**
- Consumes: `_client`, `_tool_call`, `CV_SCHEMA` from Task 1.
- Produces: `importar_cv(texto: str, perfil: str) -> dict` — calls Claude, writes `data/<perfil>-cv.json`, returns the parsed CV dict.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cv.py (add to the file from Task 1)
import json
from pathlib import Path
from unittest.mock import MagicMock

import cv

CV_EJEMPLO = {
    "basics": {"name": "Jorge Pérez", "label": "Arquitecto", "summary": "Arquitecto con 10 años de experiencia."},
    "work": [
        {"name": "Estudio A", "position": "Arquitecto Junior", "startDate": "2016", "endDate": "2019"},
        {"name": "Estudio B", "position": "Arquitecto Senior", "startDate": "2019", "endDate": "2026"},
    ],
    "education": [{"institution": "Universidad de Chile", "area": "Arquitectura", "studyType": "Licenciatura"}],
    "skills": [{"name": "AutoCAD"}, {"name": "Revit"}],
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cv.py::test_importar_cv_llama_api_y_guarda -v`
Expected: FAIL — `AttributeError: module 'cv' has no attribute 'importar_cv'`.

- [ ] **Step 3: Write minimal implementation**

```python
# cv.py — add below the existing code from Task 1
import json
from pathlib import Path


def importar_cv(texto: str, perfil: str) -> dict:
    client = _client()
    prompt = (
        "Estructura el siguiente CV en el formato JSON Resume estándar "
        "(basics, work, education, skills). No inventes información que no esté "
        "en el texto original.\n\n---\n\n" + texto
    )
    cv_data = _tool_call(
        client, "estructurar_cv", "Estructura un CV en formato JSON Resume.", CV_SCHEMA, prompt
    )
    path = Path("data") / f"{perfil}-cv.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cv_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return cv_data
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cv.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add cv.py tests/test_cv.py
git commit -m "feat: add importar_cv (Anthropic API -> JSON Resume file)"
```

---

### Task 3: `storage.obtener_por_url`

**Files:**
- Modify: `storage.py`
- Modify: `tests/test_storage.py`

**Interfaces:**
- Produces: `obtener_por_url(path, url: str) -> dict | None`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_storage.py (add to the existing file)
def test_obtener_por_url_encuentra_oferta(tmp_path):
    db = tmp_path / "test.db"
    oferta = {
        "url": "https://a.cl/1", "titulo": "Arquitecto", "empresa": "X", "ubicacion": "Santiago",
        "fecha_publicacion": "2026-04-01", "descripcion": "d", "fuente": "test.cl",
    }
    storage.guardar([oferta], db)
    encontrada = storage.obtener_por_url(db, "https://a.cl/1")
    assert encontrada is not None
    assert encontrada["titulo"] == "Arquitecto"


def test_obtener_por_url_retorna_none_si_no_existe(tmp_path):
    db = tmp_path / "test.db"
    storage.init_db(db)
    assert storage.obtener_por_url(db, "https://no-existe.cl/1") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_storage.py -v`
Expected: FAIL — `AttributeError: module 'storage' has no attribute 'obtener_por_url'`.

- [ ] **Step 3: Write minimal implementation**

```python
# storage.py — add below listar()
def obtener_por_url(path, url: str) -> dict | None:
    init_db(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM ofertas WHERE url = ?", (url,)).fetchone()
    conn.close()
    return dict(row) if row else None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_storage.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add storage.py tests/test_storage.py
git commit -m "feat: add storage.obtener_por_url for single-offer lookup"
```

---

### Task 4: `tailorear_cv`

**Files:**
- Modify: `cv.py`
- Modify: `tests/test_cv.py`

**Interfaces:**
- Consumes: `_client`, `_tool_call`, `TAILOR_SCHEMA`, `_aplicar_orden` from Task 1.
- Produces: `tailorear_cv(cv_base: dict, oferta: dict) -> dict` — never mutates `cv_base`; returns a new dict with `work`/`skills` reordered (same length/contents) and `basics.summary` replaced.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cv.py (add to the file)
import copy

OFERTA_EJEMPLO = {
    "titulo": "Arquitecto de Aplicaciones", "empresa": "AFP Habitat", "ubicacion": "Providencia",
    "descripcion": "Buscamos arquitecto senior con experiencia en sistemas de información.",
    "url": "https://x.cl/1", "fuente": "laborum.cl",
}


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cv.py -v`
Expected: FAIL — `AttributeError: module 'cv' has no attribute 'tailorear_cv'`.

- [ ] **Step 3: Write minimal implementation**

```python
# cv.py — add below importar_cv()
def tailorear_cv(cv_base: dict, oferta: dict) -> dict:
    client = _client()
    prompt = (
        "Este es un CV en formato JSON Resume:\n\n"
        + json.dumps(cv_base, ensure_ascii=False)
        + "\n\nEsta es la oferta de trabajo a la que se quiere postular:\n\n"
        f"Título: {oferta.get('titulo', '')}\n"
        f"Empresa: {oferta.get('empresa', '')}\n"
        f"Descripción: {oferta.get('descripcion', '')}\n\n"
        "Indica el orden en que deberían aparecer las entradas de work y skills "
        "(por índice, más relevante primero para esta oferta) y escribe un resumen "
        "profesional nuevo adaptado a esta oferta. No inventes experiencia, fechas "
        "ni logros que no estén en el CV original — solo reordena y resume."
    )
    resultado = _tool_call(
        client, "tailorear_cv", "Prioriza secciones de un CV para una oferta específica.", TAILOR_SCHEMA, prompt
    )

    tailored = json.loads(json.dumps(cv_base))  # copia profunda, nunca muta cv_base
    tailored["work"] = _aplicar_orden(tailored.get("work", []), resultado["orden_work"])
    tailored["skills"] = _aplicar_orden(tailored.get("skills", []), resultado["orden_skills"])
    tailored.setdefault("basics", {})["summary"] = resultado["summary"]
    return tailored
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cv.py -v`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
git add cv.py tests/test_cv.py
git commit -m "feat: add tailorear_cv (reorder work/skills + new summary per offer)"
```

---

### Task 5: `renderizar_cv` and `id_oferta`

**Files:**
- Modify: `cv.py`
- Modify: `tests/test_cv.py`

**Interfaces:**
- Produces: `id_oferta(url: str) -> str` (stable 12-char id derived from the URL), `renderizar_cv(json_path: Path, output_path: Path) -> None` (raises `RuntimeError` with an actionable message if `resumed` isn't installed; raises `RuntimeError` wrapping the underlying error if `resumed` exits non-zero).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cv.py (add to the file)
import subprocess
from pathlib import Path


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

    with pytest.raises(RuntimeError, match="npm install -g resumed"):
        cv.renderizar_cv(tmp_path / "cv.json", tmp_path / "cv.pdf")


def test_renderizar_cv_error_si_resumed_falla(tmp_path, monkeypatch):
    def fake_run(args, **kwargs):
        raise subprocess.CalledProcessError(1, args, stderr=b"theme not found")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RuntimeError):
        cv.renderizar_cv(tmp_path / "cv.json", tmp_path / "cv.pdf")
```

Add `import pytest` at the top of `tests/test_cv.py` if not already present (needed for `pytest.raises`).

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cv.py -v`
Expected: FAIL — `AttributeError: module 'cv' has no attribute 'id_oferta'`.

- [ ] **Step 3: Write minimal implementation**

```python
# cv.py — add imports at top: hashlib, subprocess
import hashlib
import subprocess


def id_oferta(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]


def renderizar_cv(json_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            ["resumed", "export", str(json_path), "-o", str(output_path), "-t", "jsonresume-theme-even"],
            check=True,
            capture_output=True,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "'resumed' no está instalado. Ejecutar: npm install -g resumed jsonresume-theme-even"
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"resumed falló al exportar el PDF: {e}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cv.py -v`
Expected: PASS (13 passed)

- [ ] **Step 5: Commit**

```bash
git add cv.py tests/test_cv.py
git commit -m "feat: add renderizar_cv (shells out to resumed) and id_oferta"
```

---

### Task 6: `cli.py` — `cv import` and `cv tailor` subcommands

**Files:**
- Modify: `cli.py`
- Modify: `tests/test_cli.py`

**Interfaces:**
- Consumes: `cv.importar_cv`, `cv.tailorear_cv`, `cv.renderizar_cv`, `cv.id_oferta` from Tasks 2/4/5; `storage.obtener_por_url` from Task 3.
- Produces: `cmd_cv_import(args) -> int`, `cmd_cv_tailor(args) -> int`, both wired into `main()`'s argparse tree under a `cv` subcommand group (`cv import`, `cv tailor`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_cli.py (add to the file)
from unittest.mock import MagicMock

import cli
import storage


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


def test_cv_tailor_sin_cv_importado_retorna_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    exit_code = cli.main(["cv", "tailor", "--profile", "arquitecto", "https://x.cl/1"])
    assert exit_code == 1


def test_cv_tailor_oferta_no_encontrada_retorna_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cv_path = tmp_path / "data" / "arquitecto-cv.json"
    cv_path.parent.mkdir(parents=True)
    cv_path.write_text('{"basics": {}, "work": [], "education": [], "skills": []}', encoding="utf-8")

    exit_code = cli.main(["cv", "tailor", "--profile", "arquitecto", "https://no-existe.cl/1"])
    assert exit_code == 1


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL — `AttributeError: module 'cli' has no attribute 'cv'` (cli.py doesn't import the `cv` module yet).

- [ ] **Step 3: Write minimal implementation**

```python
# cli.py — add near the top, alongside `import storage`
import json

import cv
```

```python
# cli.py — add these two functions near cmd_mark
def cmd_cv_import(args) -> int:
    texto = Path(args.archivo).read_text(encoding="utf-8")
    try:
        cv.importar_cv(texto, args.profile)
    except Exception as e:
        console.print(f"[bold red]Error al llamar a la API de Claude: {e}[/bold red]")
        return 1
    console.print(f"[bold green]✓ CV importado para el perfil '{args.profile}'[/bold green]")
    return 0


def cmd_cv_tailor(args) -> int:
    cv_path = Path("data") / f"{args.profile}-cv.json"
    if not cv_path.exists():
        console.print(
            f"[bold red]No hay CV importado para '{args.profile}'. "
            f"Corre 'cli.py cv import <archivo> --profile {args.profile}' primero.[/bold red]"
        )
        return 1
    cv_base = json.loads(cv_path.read_text(encoding="utf-8"))

    oferta = storage.obtener_por_url(_db_path(args.profile), args.url)
    if not oferta:
        console.print(f"[bold red]No se encontró ninguna oferta con url {args.url!r}[/bold red]")
        return 1

    try:
        tailored = cv.tailorear_cv(cv_base, oferta)
    except Exception as e:
        console.print(f"[bold red]Error al llamar a la API de Claude: {e}[/bold red]")
        return 1
    oferta_id = cv.id_oferta(args.url)
    tailored_dir = Path("data") / f"{args.profile}-tailored"
    tailored_dir.mkdir(parents=True, exist_ok=True)
    json_path = tailored_dir / f"{oferta_id}.json"
    json_path.write_text(json.dumps(tailored, ensure_ascii=False, indent=2), encoding="utf-8")

    pdf_path = tailored_dir / f"{oferta_id}.pdf"
    try:
        cv.renderizar_cv(json_path, pdf_path)
    except RuntimeError as e:
        console.print(f"[bold red]{e}[/bold red]")
        return 1

    console.print(f"[bold green]✓ Resume generado: {pdf_path}[/bold green]")
    return 0
```

```python
# cli.py — inside main(), after the existing p_mark block and before `args = parser.parse_args(argv)`
    p_cv = sub.add_parser("cv")
    cv_sub = p_cv.add_subparsers(dest="cv_comando", required=True)

    p_cv_import = cv_sub.add_parser("import")
    p_cv_import.add_argument("archivo")
    p_cv_import.add_argument("--profile", required=True)
    p_cv_import.set_defaults(func=cmd_cv_import)

    p_cv_tailor = cv_sub.add_parser("tailor")
    p_cv_tailor.add_argument("--profile", required=True)
    p_cv_tailor.add_argument("url")
    p_cv_tailor.set_defaults(func=cmd_cv_tailor)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -v`
Expected: PASS (10 passed)

- [ ] **Step 5: Commit**

```bash
git add cli.py tests/test_cli.py
git commit -m "feat: add 'cv import' and 'cv tailor' CLI subcommands"
```

---

### Task 7: Full verification pass

**Files:** none (verification only)

- [ ] **Step 1: Run the entire test suite**

Run: `pytest -v`
Expected: all tests pass — every prior module's tests plus `test_cv.py`'s 13 tests, `test_storage.py`'s 2 new tests, `test_cli.py`'s 4 new tests. Zero real network/subprocess calls (all mocked).

- [ ] **Step 2: Confirm `data/` artifacts aren't tracked by git**

```bash
git status --short
```

Expected: no untracked files under `data/` show up (it's gitignored) even after running the test suite, which writes to `tmp_path` fixtures, not the repo's own `data/`.

- [ ] **Step 3: Manually verify the CLI wiring (no real API calls — just argument parsing and error paths)**

```bash
python3 cli.py cv tailor --profile arquitecto https://no-existe.cl/1
```

Expected: prints `No hay CV importado para 'arquitecto'. Corre 'cli.py cv import <archivo> --profile arquitecto' primero.` and exits 1 (no traceback, no API key required since it fails before reaching `cv.tailorear_cv`).

```bash
python3 cli.py cv import --help
python3 cli.py cv tailor --help
```

Expected: both print usage help without error.

- [ ] **Step 4: Document the real prerequisites in a note for the human operator**

This step is documentation only, not code — confirm (by reading, not running) that the spec's "Uso" section already covers: `pip install anthropic`, `npm install -g resumed jsonresume-theme-even`, and `export ANTHROPIC_API_KEY=...`. No file changes needed if `docs/superpowers/specs/2026-08-03-cv-tailoring-design.md` already has this (it does, per the approved spec) — this step is a sanity check, not a task deliverable.

- [ ] **Step 5: Final commit (only if step 1-3 surfaced something to fix)**

```bash
git add -A
git commit -m "test: verify full suite green after CV tailoring pipeline"
```
