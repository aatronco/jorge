# Generic Multi-Profile Scraper + Matrix CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repurpose the Químico-Farmacéutico-specific job scraper into a profile-driven, profession-agnostic scraper with local SQLite tracking and a Matrix-themed terminal CLI, per `docs/superpowers/specs/2026-08-03-generic-scraper-cli-design.md`.

**Architecture:** Scrapers self-register into a module-level dict via a `@register(name)` decorator (`scrapers/registry.py`). Two base classes replace the flat `BaseScraper`: `KeywordSearchScraper` (query-based sites) and `PortalListScraper` (multi-institution portals sharing one HTML layout). A YAML profile (`profiles/<name>.yaml`) supplies `keywords` and the list of scrapers to activate; `run.py` resolves scraper names against the registry and instantiates them with the profile's config. Results land in a per-profile SQLite file (`storage.py`) that never overwrites an existing row's `estado`. `cli.py` reads/writes that same SQLite file to list offers and mark status, with a skippable `cmatrix`-style splash.

**Tech Stack:** Python 3.12, `requests` + `beautifulsoup4` + `lxml` (static scraping), `playwright` (JS-rendered sites), `PyYAML` (profiles), `rich` (CLI rendering/animation), `pytest` + `responses` (tests), stdlib `sqlite3` (storage), stdlib `argparse` (CLI).

## Global Constraints

- Target Python version: 3.12 (matches the project's prior CI config; no version-specific syntax beyond what's already in the codebase).
- `BaseScraper._make_oferta()` must keep returning a dict with exactly these keys, unchanged: `titulo, empresa, ubicacion, fecha_publicacion, descripcion, url, fuente`. Many existing tests assert this exact key set — do not add/remove keys.
- `storage.guardar()` must never overwrite the `estado` of a row that already exists (matched by `url`) — this is the core behavior the whole CLI depends on.
- The CLI splash animation must be skippable via a `--no-anim` flag on every subcommand — required for scripting and for tests to run without sleeping.
- No dependency on `gspread` / `google-auth` / Google Sheets may remain anywhere in the codebase after this plan.
- No GitHub Actions workflow remains after this plan (per spec: local-only, no CI).
- Deviation from the committed spec, noted here for the record: the spec text mentions a per-profile `location_filter`. This plan keeps geographic filtering exactly as it works today — the module-level `is_region_metropolitana()` in `scrapers/base.py`, hardcoded to Chile's Región Metropolitana — rather than inventing a new multi-region config no current profile (QF or Arquitecto) actually needs. Both profiles target Región Metropolitana, Chile. Add real `location_filter` parametrization later if/when a profile needs a different region.

---

### Task 1: Scraper registry

**Files:**
- Create: `scrapers/registry.py`
- Test: `tests/test_registry.py`

**Interfaces:**
- Produces: `register(nombre: str) -> Callable[[type], type]` (class decorator), `get(nombre: str) -> type` (raises `KeyError` if unregistered), `all_names() -> list[str]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_registry.py
import pytest
from scrapers import registry


def test_register_and_get():
    @registry.register("dummy_test_scraper")
    class Dummy:
        pass

    assert registry.get("dummy_test_scraper") is Dummy


def test_get_unregistered_raises_keyerror():
    with pytest.raises(KeyError):
        registry.get("no_existe_este_scraper")


def test_all_names_incluye_registrados():
    @registry.register("otro_dummy")
    class Otro:
        pass

    assert "otro_dummy" in registry.all_names()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_registry.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scrapers.registry'` (or `ImportError`).

- [ ] **Step 3: Write minimal implementation**

```python
# scrapers/registry.py
_REGISTRY: dict[str, type] = {}


def register(nombre: str):
    def decorator(cls):
        _REGISTRY[nombre] = cls
        return cls
    return decorator


def get(nombre: str) -> type:
    if nombre not in _REGISTRY:
        raise KeyError(f"Scraper no registrado: {nombre!r}. Disponibles: {sorted(_REGISTRY)}")
    return _REGISTRY[nombre]


def all_names() -> list[str]:
    return sorted(_REGISTRY)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_registry.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add scrapers/registry.py tests/test_registry.py
git commit -m "feat: add scraper registry decorator"
```

---

### Task 2: Split BaseScraper into KeywordSearchScraper and PortalListScraper

**Files:**
- Modify: `scrapers/base.py`
- Modify: `tests/test_base.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `BaseScraper.__init__(self, keywords: list[str])` sets `self.keywords`. `KeywordSearchScraper(BaseScraper)` — no extra behavior, just the semantic name every keyword-search site subclasses. `PortalListScraper(BaseScraper).__init__(self, keywords: list[str], portales: list[dict])` sets `self.portales` (each dict has `nombre`, `base_url`, `fuente`). `is_region_metropolitana(ubicacion)` unchanged (module function, no parametrization — see Global Constraints deviation note).

Current `scrapers/base.py` (for reference, being replaced):

```python
class BaseScraper(ABC):
    KEYWORDS = ("Químico Farmacéutico", "QF")

    @abstractmethod
    def fetch(self) -> list[dict]:
        pass

    def _make_oferta(self, titulo, empresa, ubicacion, fecha, descripcion, url, fuente) -> dict:
        return {...}
```

- [ ] **Step 1: Update the failing test first**

Edit `tests/test_base.py` — every place that does `Concreto()` becomes `Concreto(keywords=["test"])`:

```python
def test_make_oferta_normaliza_none():
    class Concreto(BaseScraper):
        def fetch(self):
            return []

    scraper = Concreto(keywords=["test"])
    oferta = scraper._make_oferta(None, None, None, None, None, None, "test")
    for k, v in oferta.items():
        if k != "fuente":
            assert v == "", f"Campo '{k}' debería ser '' pero es {v!r}"
    assert oferta["fuente"] == "test"


def test_make_oferta_normaliza_fuente_none():
    class Concreto(BaseScraper):
        def fetch(self):
            return []
    scraper = Concreto(keywords=["test"])
    oferta = scraper._make_oferta(None, None, None, None, None, None, None)
    assert oferta["fuente"] == ""


def test_make_oferta_estructura_completa():
    class Concreto(BaseScraper):
        def fetch(self):
            return []

    scraper = Concreto(keywords=["test"])
    oferta = scraper._make_oferta("QF", "Lab", "Santiago", "2026-04-01", "desc", "https://x.cl", "fuente")
    assert set(oferta.keys()) == {
        "titulo", "empresa", "ubicacion", "fecha_publicacion", "descripcion", "url", "fuente"
    }
```

Also add two new tests to the same file:

```python
def test_keyword_search_scraper_guarda_keywords():
    from scrapers.base import KeywordSearchScraper

    class Concreto(KeywordSearchScraper):
        def fetch(self):
            return []

    scraper = Concreto(keywords=["Arquitecto", "Arquitectura"])
    assert scraper.keywords == ["Arquitecto", "Arquitectura"]


def test_portal_list_scraper_guarda_portales():
    from scrapers.base import PortalListScraper

    class Concreto(PortalListScraper):
        def fetch(self):
            return []

    portales = [{"nombre": "x", "base_url": "https://x.cl", "fuente": "x.cl"}]
    scraper = Concreto(keywords=["QF"], portales=portales)
    assert scraper.portales == portales
    assert scraper.keywords == ["QF"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_base.py -v`
Expected: FAIL — `TypeError: BaseScraper.__init__() got an unexpected keyword argument 'keywords'` (or `ImportError` for `KeywordSearchScraper`).

- [ ] **Step 3: Write minimal implementation**

```python
# scrapers/base.py
from abc import ABC, abstractmethod

_RM_KEYWORDS = [
    "metropolitana", "santiago", ", rm", ", rm ", "(rm)", "providencia",
    "las condes", "ñuñoa", "maipú", "maipu", "la florida",
    "puente alto", "vitacura", "lo barnechea", "peñalolén", "penalolen",
    "macul", "san miguel", "estación central", "recoleta", "independencia",
    "quilicura", "pudahuel", "la pintana", "cerrillos", "el bosque",
    "san ramón", "la granja", "lo espejo", "pedro aguirre cerda",
    "san joaquín", "lo prado", "quinta normal", "cerro navia",
    "renca", "huechuraba", "conchalí", "colina", "lampa", "til til", "tiltil",
    "pirque", "san josé de maipo", "talagante", "peñaflor", "isla de maipo",
    "el monte", "padre hurtado", "calera de tango", "san bernardo",
    "buin", "paine", "melipilla",
]


def is_region_metropolitana(ubicacion) -> bool:
    """Retorna True si la ubicación pertenece a la RM, o si está vacía."""
    if not ubicacion:
        return True
    lower = ubicacion.lower()
    return any(kw in lower for kw in _RM_KEYWORDS)


class BaseScraper(ABC):
    def __init__(self, keywords: list[str]):
        self.keywords = list(keywords)

    @abstractmethod
    def fetch(self) -> list[dict]:
        """Retorna lista de ofertas en formato estándar."""
        pass

    def _make_oferta(
        self,
        titulo,
        empresa,
        ubicacion,
        fecha,
        descripcion,
        url,
        fuente: str,
    ) -> dict:
        return {
            "titulo": titulo or "",
            "empresa": empresa or "",
            "ubicacion": ubicacion or "",
            "fecha_publicacion": fecha or "",
            "descripcion": descripcion or "",
            "url": url or "",
            "fuente": fuente or "",
        }


class KeywordSearchScraper(BaseScraper):
    """Sitios que se buscan pasando una keyword como query (Computrabajo, Indeed, etc)."""


class PortalListScraper(BaseScraper):
    """Sitios con múltiples instituciones/sub-portales que comparten un mismo layout."""

    def __init__(self, keywords: list[str], portales: list[dict]):
        super().__init__(keywords)
        self.portales = list(portales)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_base.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add scrapers/base.py tests/test_base.py
git commit -m "refactor: parametrize BaseScraper keywords, split search/portal-list bases"
```

---

### Task 3: Migrate Computrabajo scraper

**Files:**
- Modify: `scrapers/computrabajo.py`
- Modify: `tests/test_computrabajo.py`

**Interfaces:**
- Consumes: `KeywordSearchScraper.__init__(keywords)`, `registry.register`.
- Produces: `ComputrabajoScraper(keywords=[...])`, registered as `"computrabajo"`.

The current `KEYWORD_SLUGS` dict hardcodes `{"Químico Farmacéutico": "qu%C3%ADmico-farmac%C3%A9utico", "QF": "qf"}`. `urllib.parse.quote(keyword.lower().replace(" ", "-"))` reproduces those exact slugs (verified: `quote("químico farmacéutico".replace(" ", "-"))` → `qu%C3%ADmico-farmac%C3%A9utico`; `quote("qf")` → `qf`), so this generalizes without changing the URLs the existing test mocks.

- [ ] **Step 1: Update the failing test first**

```python
# tests/test_computrabajo.py
import responses as responses_lib
from pathlib import Path
from unittest.mock import patch
from scrapers.computrabajo import ComputrabajoScraper

FIXTURE = (Path(__file__).parent / "fixtures" / "computrabajo_sample.html").read_text(encoding="utf-8")
KEYWORDS = ["Químico Farmacéutico", "QF"]


def test_parse_filtra_rm():
    scraper = ComputrabajoScraper(keywords=KEYWORDS)
    ofertas = scraper._parse_html(FIXTURE)
    assert len(ofertas) == 2
    assert "Bagó" in ofertas[0]["empresa"]
    assert "Santiago" in ofertas[0]["ubicacion"]


def test_parse_excluye_concepcion():
    scraper = ComputrabajoScraper(keywords=KEYWORDS)
    ofertas = scraper._parse_html(FIXTURE)
    assert not any("Concepción" in o["ubicacion"] for o in ofertas)


def test_parse_estructura_oferta():
    scraper = ComputrabajoScraper(keywords=KEYWORDS)
    ofertas = scraper._parse_html(FIXTURE)
    oferta = ofertas[0]
    assert set(oferta.keys()) == {
        "titulo", "empresa", "ubicacion", "fecha_publicacion", "descripcion", "url", "fuente"
    }
    assert oferta["fuente"] == "computrabajo.cl"
    assert "cl.computrabajo.com" in oferta["url"]
    assert oferta["titulo"] == "QF Aseguramiento de Calidad"


@responses_lib.activate
def test_fetch_hace_request_por_keyword():
    responses_lib.add(responses_lib.GET, "https://cl.computrabajo.com/trabajo-de-qu%C3%ADmico-farmac%C3%A9utico",
                      body=FIXTURE, status=200)
    responses_lib.add(responses_lib.GET, "https://cl.computrabajo.com/trabajo-de-qf",
                      body=FIXTURE, status=200)
    with patch("scrapers.computrabajo.time.sleep"):
        scraper = ComputrabajoScraper(keywords=KEYWORDS)
        ofertas = scraper.fetch()
    assert len(ofertas) >= 1
    assert all(o["fuente"] == "computrabajo.cl" for o in ofertas)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_computrabajo.py -v`
Expected: FAIL — `TypeError: ComputrabajoScraper.__init__() missing 1 required positional argument` (constructor still takes no args).

- [ ] **Step 3: Write minimal implementation**

```python
# scrapers/computrabajo.py
import time
from urllib.parse import quote
import requests
from bs4 import BeautifulSoup
from scrapers.base import KeywordSearchScraper, is_region_metropolitana
from scrapers.registry import register

# Selectores verificados en HTML real (2026-04-03):
SEL_CARD = "article.box_offer"
SEL_TITULO = "h2 a"
SEL_EMPRESA = "p.dFlex"                   # párrafo con empresa (tiene clase dFlex)
SEL_UBICACION = "span.mr10:not(.fx_none)" # span de ubicación (excluye el span de rating)
SEL_FECHA = "p.fs13"                      # párrafo de fecha relativa


@register("computrabajo")
class ComputrabajoScraper(KeywordSearchScraper):
    def _parse_html(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        ofertas = []
        for card in soup.select(SEL_CARD):
            titulo_tag = card.select_one(SEL_TITULO)
            if not titulo_tag:
                continue
            titulo = titulo_tag.get_text(strip=True)
            href = titulo_tag.get("href", "")
            url = f"https://cl.computrabajo.com{href}" if href.startswith("/") else href
            empresa = card.select_one(SEL_EMPRESA)
            empresa = empresa.get_text(strip=True) if empresa else ""
            ubicacion = card.select_one(SEL_UBICACION)
            ubicacion = ubicacion.get_text(strip=True) if ubicacion else ""
            fecha = card.select_one(SEL_FECHA)
            fecha = fecha.get_text(strip=True) if fecha else ""
            if not is_region_metropolitana(ubicacion):
                continue
            ofertas.append(
                self._make_oferta(titulo, empresa, ubicacion, fecha, "", url, "computrabajo.cl")
            )
        return ofertas

    def fetch(self) -> list[dict]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "es-CL,es;q=0.9",
        }
        ofertas = []
        for keyword in self.keywords:
            slug = quote(keyword.lower().replace(" ", "-"))
            url = f"https://cl.computrabajo.com/trabajo-de-{slug}"
            params = {"where": "Región Metropolitana"}
            try:
                resp = requests.get(url, params=params, headers=headers, timeout=15)
                resp.raise_for_status()
            except requests.RequestException as e:
                print(f"[computrabajo.cl] Error al buscar '{keyword}': {e}")
                continue
            ofertas.extend(self._parse_html(resp.text))
            time.sleep(1)
        return ofertas
```

Note: the unused `from fake_useragent import UserAgent` import is dropped — it was never used in the original file.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_computrabajo.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add scrapers/computrabajo.py tests/test_computrabajo.py
git commit -m "refactor: parametrize Computrabajo scraper keywords, register it, drop unused import"
```

---

### Task 4: Migrate Indeed scraper

**Files:**
- Modify: `scrapers/indeed.py`
- Modify: `tests/test_indeed.py`

**Interfaces:**
- Consumes: `KeywordSearchScraper.__init__(keywords)`, `registry.register`.
- Produces: `IndeedScraper(keywords=[...])`, registered as `"indeed"`.

This file already loops `for keyword in self.KEYWORDS:` — the only change is renaming that class attribute reference to the new instance attribute `self.keywords`, subclassing `KeywordSearchScraper`, and registering it.

- [ ] **Step 1: Update the failing test first**

```python
# tests/test_indeed.py
from pathlib import Path
from scrapers.indeed import IndeedScraper

FIXTURE = (Path(__file__).parent / "fixtures" / "indeed_sample.html").read_text(encoding="utf-8")
KEYWORDS = ["Químico Farmacéutico", "QF"]


def test_parse_filtra_rm():
    scraper = IndeedScraper(keywords=KEYWORDS)
    ofertas = scraper._parse_html(FIXTURE)
    assert len(ofertas) == 1
    assert "Maver" in ofertas[0]["empresa"]
    assert "Santiago" in ofertas[0]["ubicacion"]


def test_parse_excluye_vina():
    scraper = IndeedScraper(keywords=KEYWORDS)
    ofertas = scraper._parse_html(FIXTURE)
    assert not any("Viña" in o["ubicacion"] for o in ofertas)


def test_parse_estructura_oferta():
    scraper = IndeedScraper(keywords=KEYWORDS)
    ofertas = scraper._parse_html(FIXTURE)
    oferta = ofertas[0]
    assert set(oferta.keys()) == {
        "titulo", "empresa", "ubicacion", "fecha_publicacion", "descripcion", "url", "fuente"
    }
    assert oferta["fuente"] == "indeed.cl"
    assert "cl.indeed.com" in oferta["url"]
    assert oferta["titulo"] == "Químico Farmacéutico Senior"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_indeed.py -v`
Expected: FAIL — `TypeError: IndeedScraper() missing 1 required positional argument: 'keywords'`.

- [ ] **Step 3: Write minimal implementation**

```python
# scrapers/indeed.py
from bs4 import BeautifulSoup
from scrapers.base import KeywordSearchScraper, is_region_metropolitana
from scrapers.registry import register

BASE_URL = "https://cl.indeed.com/jobs"

# Selectores verificados en HTML real con anti-detección (2026-04-03).
# Indeed cambia selectores frecuentemente — re-verificar si vuelve a dar 0 resultados.
SEL_CARD = "div.result"
SEL_TITULO = "h2.jobTitle a"
SEL_EMPRESA = "span[data-testid='company-name']"
SEL_UBICACION = "div[data-testid='text-location']"
SEL_FECHA = ""  # indeed.cl no muestra fecha en la vista de lista


@register("indeed")
class IndeedScraper(KeywordSearchScraper):
    def _parse_html(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        ofertas = []
        for card in soup.select(SEL_CARD):
            titulo_tag = card.select_one(SEL_TITULO)
            if not titulo_tag:
                continue
            titulo = titulo_tag.get_text(strip=True)
            href = titulo_tag.get("href", "")
            if href.startswith("/"):
                url = f"https://cl.indeed.com{href}"
            elif href.startswith("http"):
                url = href
            else:
                url = f"https://cl.indeed.com/viewjob?jk={href}"
            empresa = card.select_one(SEL_EMPRESA)
            empresa = empresa.get_text(strip=True) if empresa else ""
            ubicacion = card.select_one(SEL_UBICACION)
            ubicacion = ubicacion.get_text(strip=True) if ubicacion else ""
            fecha = card.select_one(SEL_FECHA) if SEL_FECHA else None
            fecha = fecha.get_text(strip=True) if fecha else ""
            if not is_region_metropolitana(ubicacion):
                continue
            ofertas.append(
                self._make_oferta(titulo, empresa, ubicacion, fecha, "", url, "indeed.cl")
            )
        return ofertas

    def fetch(self) -> list[dict]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("[indeed.cl] playwright no instalado. Ejecutar: playwright install chromium")
            return []

        from urllib.parse import urlencode

        ofertas = []
        with sync_playwright() as p:
            with p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            ) as browser:
                ctx = browser.new_context(
                    viewport={"width": 1280, "height": 900},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                )
                page = ctx.new_page()
                page.add_init_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                )
                page.set_extra_http_headers({"Accept-Language": "es-CL,es;q=0.9"})
                for keyword in self.keywords:
                    try:
                        params = urlencode({"q": keyword, "l": "Región Metropolitana, Chile"})
                        url = f"{BASE_URL}?{params}"
                        page.goto(url, timeout=20000)
                        page.wait_for_selector(SEL_CARD, timeout=10000)
                        html = page.content()
                        ofertas.extend(self._parse_html(html))
                    except Exception as e:
                        print(f"[indeed.cl] {type(e).__name__} al buscar '{keyword}': {e}")
        return ofertas
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_indeed.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add scrapers/indeed.py tests/test_indeed.py
git commit -m "refactor: parametrize Indeed scraper keywords, register it"
```

---

### Task 5: Migrate BNE scraper

**Files:**
- Modify: `scrapers/bne.py`

**Interfaces:**
- Consumes: `KeywordSearchScraper.__init__(keywords)`, `registry.register`.
- Produces: `BneScraper(keywords=[...])`, registered as `"bne"`.

No test file exists for this scraper today (pre-existing gap — no `test_bne.py`, no fixture). This task only renames the class attribute reference and registers it; it does not add new test coverage (out of scope for this plan — flagged here for visibility, not silently fixed).

- [ ] **Step 1: Modify the scraper**

```python
# scrapers/bne.py
"""
Scraper para Bolsa Nacional de Empleo (bne.cl)
El sitio renderiza resultados vía JavaScript — requiere Playwright.

Selectores verificados en HTML real (2026-04-05).
"""
from bs4 import BeautifulSoup
from scrapers.base import KeywordSearchScraper, is_region_metropolitana
from scrapers.registry import register

BASE_URL = "https://www.bne.cl/ofertas"
SEL_CARD      = "article.resultadoOfertas"
SEL_TITULO    = "div.tituloOferta a"
SEL_EMPRESA   = "div.datosEmpresaOferta div:first-child"
SEL_UBICACION = "div.datosEmpresaOferta div:last-child"
SEL_FECHA     = "span.fechaOferta"
SEL_DESC      = "div.descripcionOferta span"


@register("bne")
class BneScraper(KeywordSearchScraper):
    def _parse_html(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        ofertas = []
        for card in soup.select(SEL_CARD):
            titulo_tag = card.select_one(SEL_TITULO)
            if not titulo_tag:
                continue
            titulo = titulo_tag.get_text(strip=True)
            href = titulo_tag.get("href", "")
            url = f"https://www.bne.cl{href}" if href.startswith("/") else href

            empresa_tag = card.select_one(SEL_EMPRESA)
            empresa = empresa_tag.get_text(strip=True) if empresa_tag else ""

            ubicacion_tag = card.select_one(SEL_UBICACION)
            ubicacion = ubicacion_tag.get_text(strip=True) if ubicacion_tag else ""

            fecha_tag = card.select_one(SEL_FECHA)
            fecha = fecha_tag.get_text(strip=True) if fecha_tag else ""

            desc_tag = card.select_one(SEL_DESC)
            descripcion = desc_tag.get_text(strip=True) if desc_tag else ""

            if not is_region_metropolitana(ubicacion):
                continue

            ofertas.append(
                self._make_oferta(titulo, empresa, ubicacion, fecha, descripcion, url, "bne.cl")
            )
        return ofertas

    def fetch(self) -> list[dict]:
        try:
            from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
        except ImportError:
            print("[bne.cl] playwright no instalado.")
            return []

        ofertas = []
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            ctx = browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            )
            page = ctx.new_page()
            page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            page.set_extra_http_headers({"Accept-Language": "es-CL,es;q=0.9"})

            for keyword in self.keywords:
                url = (
                    f"{BASE_URL}?mostrar=empleo"
                    f"&textoLibre={keyword.replace(' ', '%20')}"
                    f"&numResultadosPorPagina=50"
                    f"&clasificarYPaginar=true"
                )
                try:
                    page.goto(url, timeout=25000)
                    page.wait_for_load_state("networkidle", timeout=15000)
                    try:
                        page.wait_for_selector(SEL_CARD, timeout=10000)
                    except PWTimeout:
                        print(f"[bne.cl] Sin resultados visibles para '{keyword}'")
                        continue
                    ofertas.extend(self._parse_html(page.content()))
                except Exception as e:
                    print(f"[bne.cl] {type(e).__name__} al buscar '{keyword}': {e}")

            browser.close()

        return ofertas
```

- [ ] **Step 2: Sanity-check the module imports cleanly**

Run: `python -c "import scrapers.bne"`
Expected: no output, exit code 0.

- [ ] **Step 3: Commit**

```bash
git add scrapers/bne.py
git commit -m "refactor: parametrize BNE scraper keywords, register it"
```

---

### Task 6: Migrate EmpleosPublicos scraper

**Files:**
- Modify: `scrapers/empleospublicos.py`
- Modify: `tests/test_empleospublicos.py`

**Interfaces:**
- Consumes: `KeywordSearchScraper.__init__(keywords)`, `registry.register`.
- Produces: `EmpleosPublicosScraper(keywords=[...])`, registered as `"empleospublicos"`. `self.keywords` now drives both the search queries sent to the site (one per keyword) and the title-filter substring match in `_parse_html` (replaces the old hardcoded `KEYWORDS_QF` list and `SEARCH_TERMS` combos).

Verified equivalence: `urllib.parse.quote_plus("químico farmacéutico")` → `qu%C3%ADmico+farmac%C3%A9utico` and `quote_plus("farmacéutico regente")` → `farmac%C3%A9utico+regente` — identical to the two hardcoded `SEARCH_TERMS` strings today, so passing `keywords=["Químico Farmacéutico", "Farmacéutico Regente"]` reproduces the exact same two HTTP requests the existing test mocks.

- [ ] **Step 1: Update the failing test first**

```python
# tests/test_empleospublicos.py
from pathlib import Path
from unittest.mock import patch
import responses as responses_lib
from scrapers.empleospublicos import EmpleosPublicosScraper

FIXTURE = (Path(__file__).parent / "fixtures" / "empleospublicos_sample.html").read_text(encoding="utf-8")
KEYWORDS = ["Químico Farmacéutico", "Farmacéutico Regente"]


def test_parse_filtra_qf():
    scraper = EmpleosPublicosScraper(keywords=KEYWORDS)
    ofertas = scraper._parse_html(FIXTURE)
    # fixture: 2 cards con "químico farmacéutico" en título, 1 card "médico cirujano" excluida
    assert len(ofertas) == 2
    titulos = [o["titulo"].lower() for o in ofertas]
    assert all("químico" in t for t in titulos)


def test_parse_excluye_no_qf():
    scraper = EmpleosPublicosScraper(keywords=KEYWORDS)
    ofertas = scraper._parse_html(FIXTURE)
    titulos = [o["titulo"] for o in ofertas]
    assert not any("MÉDICO CIRUJANO" in t for t in titulos)


def test_parse_estructura_oferta():
    scraper = EmpleosPublicosScraper(keywords=KEYWORDS)
    ofertas = scraper._parse_html(FIXTURE)
    assert len(ofertas) > 0
    oferta = ofertas[0]
    assert set(oferta.keys()) == {
        "titulo", "empresa", "ubicacion", "fecha_publicacion", "descripcion", "url", "fuente"
    }
    assert oferta["fuente"] == "empleospublicos.cl"
    assert oferta["ubicacion"] == ""  # intencionalmente vacío — incluye empleos de todo Chile
    assert "La Florida" in oferta["empresa"]
    assert oferta["url"].startswith("https://www.empleospublicos.cl/pub/convocatorias/")
    assert "2026" in oferta["fecha_publicacion"]


@responses_lib.activate
def test_fetch_hace_request():
    url1 = "https://www.empleospublicos.cl/pub/convocatorias/convocatorias.aspx?busqueda=qu%C3%ADmico+farmac%C3%A9utico"
    url2 = "https://www.empleospublicos.cl/pub/convocatorias/convocatorias.aspx?busqueda=farmac%C3%A9utico+regente"
    responses_lib.add(responses_lib.GET, url1, body=FIXTURE, status=200)
    responses_lib.add(responses_lib.GET, url2, body=FIXTURE, status=200)
    with patch("scrapers.empleospublicos.time.sleep"):
        scraper = EmpleosPublicosScraper(keywords=KEYWORDS)
        ofertas = scraper.fetch()
    assert isinstance(ofertas, list)
    assert all(o["fuente"] == "empleospublicos.cl" for o in ofertas)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_empleospublicos.py -v`
Expected: FAIL — `TypeError: EmpleosPublicosScraper() missing 1 required positional argument: 'keywords'`.

- [ ] **Step 3: Write minimal implementation**

```python
# scrapers/empleospublicos.py
import time
from urllib.parse import quote_plus
import requests
from bs4 import BeautifulSoup
from scrapers.base import KeywordSearchScraper
from scrapers.registry import register

BASE_CONV = "https://www.empleospublicos.cl/pub/convocatorias/"
SEARCH_URL = BASE_CONV + "convocatorias.aspx"

SEL_CARD   = "div.caja.row"
SEL_TITULO = "#bx_titulos"
SEL_EMPRESA = "#bx_resumen strong"
SEL_FECHA  = "#bx_resumen em"
SEL_DESC   = "#bx_resumen"
SEL_URL    = "a.btnverficha"


@register("empleospublicos")
class EmpleosPublicosScraper(KeywordSearchScraper):
    def _parse_html(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        ofertas = []
        seen_urls: set[str] = set()
        for card in soup.select(SEL_CARD):
            titulo_el = card.select_one(SEL_TITULO)
            if not titulo_el:
                continue
            titulo = titulo_el.get_text(strip=True)
            if not any(kw.lower() in titulo.lower() for kw in self.keywords):
                continue
            empresa_el = card.select_one(SEL_EMPRESA)
            empresa = empresa_el.get_text(strip=True) if empresa_el else ""
            fecha_el = card.select_one(SEL_FECHA)
            fecha = fecha_el.get_text(strip=True) if fecha_el else ""
            desc_el = card.select_one(SEL_DESC)
            desc = ""
            if desc_el:
                raw = desc_el.get_text(separator=" ", strip=True)
                raw = raw.replace(empresa, "").replace(fecha, "").strip()
                desc = " ".join(raw.split())
            url_el = card.select_one(SEL_URL)
            href = url_el.get("href", "") if url_el else ""
            url = BASE_CONV + href if href and not href.startswith("http") else href
            if url in seen_urls:
                continue
            seen_urls.add(url)
            # ubicacion vacío → is_region_metropolitana devuelve True (incluir todos los empleos públicos)
            ofertas.append(
                self._make_oferta(titulo, empresa, "", fecha, desc, url, "empleospublicos.cl")
            )
        return ofertas

    def fetch(self) -> list[dict]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "es-CL,es;q=0.9",
        }
        all_offers: list[dict] = []
        seen_urls: set[str] = set()
        for keyword in self.keywords:
            term = quote_plus(keyword.lower())
            url = f"{SEARCH_URL}?busqueda={term}"
            try:
                resp = requests.get(url, headers=headers, timeout=20)
                resp.raise_for_status()
            except requests.RequestException as e:
                print(f"[empleospublicos.cl] Error al buscar '{keyword}': {e}")
                continue
            for oferta in self._parse_html(resp.text):
                if oferta["url"] not in seen_urls:
                    seen_urls.add(oferta["url"])
                    all_offers.append(oferta)
            time.sleep(1)
        return all_offers
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_empleospublicos.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add scrapers/empleospublicos.py tests/test_empleospublicos.py
git commit -m "refactor: parametrize EmpleosPublicos keywords for search and title filter"
```

---

### Task 7: Migrate Laborum and Trabajando scrapers (blocked-site stubs)

**Files:**
- Modify: `scrapers/laborum.py`
- Modify: `scrapers/trabajando.py`
- Modify: `tests/test_laborum.py`
- Modify: `tests/test_trabajando.py`

**Interfaces:**
- Consumes: `KeywordSearchScraper.__init__(keywords)`, `registry.register`.
- Produces: `LaborumScraper(keywords=[...])` registered as `"laborum"`; `TrabajandoScraper(keywords=[...])` registered as `"trabajando"`. Neither uses `self.keywords` in its logic today (both sites actively block automation and `fetch()` returns `[]`) — the parameter exists for interface consistency and for when either site becomes scrapeable again.

- [ ] **Step 1: Update the failing tests first**

```python
# tests/test_laborum.py
from pathlib import Path
from scrapers.laborum import LaborumScraper

FIXTURE = (Path(__file__).parent / "fixtures" / "laborum_sample.html").read_text(encoding="utf-8")


def test_parse_filtra_rm():
    scraper = LaborumScraper(keywords=["Químico Farmacéutico"])
    ofertas = scraper._parse_html(FIXTURE)
    assert len(ofertas) == 1
    assert "Recalcine" in ofertas[0]["empresa"]
    assert "Santiago" in ofertas[0]["ubicacion"]


def test_parse_excluye_talca():
    scraper = LaborumScraper(keywords=["Químico Farmacéutico"])
    ofertas = scraper._parse_html(FIXTURE)
    assert not any("Talca" in o["ubicacion"] for o in ofertas)


def test_parse_estructura_oferta():
    scraper = LaborumScraper(keywords=["Químico Farmacéutico"])
    ofertas = scraper._parse_html(FIXTURE)
    oferta = ofertas[0]
    assert set(oferta.keys()) == {
        "titulo", "empresa", "ubicacion", "fecha_publicacion", "descripcion", "url", "fuente"
    }
    assert oferta["fuente"] == "laborum.com"
    assert oferta["url"].startswith("https://www.laborum.com")
    assert "2026" in oferta["fecha_publicacion"]


def test_fetch_retorna_vacio_sitio_bloqueado(capsys):
    scraper = LaborumScraper(keywords=["Químico Farmacéutico"])
    ofertas = scraper.fetch()
    assert ofertas == []
    captured = capsys.readouterr()
    assert "bloquea" in captured.out.lower() or "skip" in captured.out.lower()
```

```python
# tests/test_trabajando.py
from pathlib import Path
from scrapers.trabajando import TrabajandoScraper

FIXTURE = (Path(__file__).parent / "fixtures" / "trabajando_sample.html").read_text(encoding="utf-8")


def test_parse_filtra_rm():
    scraper = TrabajandoScraper(keywords=["Químico Farmacéutico"])
    ofertas = scraper._parse_html(FIXTURE)
    assert len(ofertas) == 1
    assert "Farmacia Chile" in ofertas[0]["empresa"]
    assert "Santiago" in ofertas[0]["ubicacion"]


def test_parse_excluye_fuera_rm():
    scraper = TrabajandoScraper(keywords=["Químico Farmacéutico"])
    ofertas = scraper._parse_html(FIXTURE)
    ubicaciones = [o["ubicacion"] for o in ofertas]
    assert not any("Valparaíso" in u for u in ubicaciones)


def test_parse_estructura_oferta():
    scraper = TrabajandoScraper(keywords=["Químico Farmacéutico"])
    ofertas = scraper._parse_html(FIXTURE)
    assert len(ofertas) > 0
    oferta = ofertas[0]
    assert set(oferta.keys()) == {
        "titulo", "empresa", "ubicacion", "fecha_publicacion", "descripcion", "url", "fuente"
    }
    assert oferta["fuente"] == "trabajando.cl"
    assert oferta["url"].startswith("https://www.trabajando.cl")
    assert oferta["titulo"] == "Químico Farmacéutico Regente"


def test_fetch_retorna_vacio_sitio_bloqueado(capsys):
    scraper = TrabajandoScraper(keywords=["Químico Farmacéutico"])
    ofertas = scraper.fetch()
    assert ofertas == []
    captured = capsys.readouterr()
    assert "bloquea" in captured.out.lower() or "skip" in captured.out.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_laborum.py tests/test_trabajando.py -v`
Expected: FAIL — `TypeError: ...Scraper() missing 1 required positional argument: 'keywords'`.

- [ ] **Step 3: Write minimal implementation**

```python
# scrapers/laborum.py
from bs4 import BeautifulSoup
from scrapers.base import KeywordSearchScraper, is_region_metropolitana
from scrapers.registry import register

BASE_URL = "https://www.laborum.com/empleos"

# Verificar en https://www.laborum.com si los selectores cambian:
SEL_CARD = "div.aviso-item"
SEL_TITULO = "a.titulo-aviso"
SEL_EMPRESA = "span.empresa"
SEL_UBICACION = "span.localidad"
SEL_FECHA = "span.fecha"
SEL_DESC = "p.extracto"


@register("laborum")
class LaborumScraper(KeywordSearchScraper):
    def _parse_html(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        ofertas = []
        for card in soup.select(SEL_CARD):
            titulo_tag = card.select_one(SEL_TITULO)
            if not titulo_tag:
                continue
            titulo = titulo_tag.get_text(strip=True)
            href = titulo_tag.get("href", "")
            url = f"https://www.laborum.com{href}" if href.startswith("/") else href
            empresa = card.select_one(SEL_EMPRESA)
            empresa = empresa.get_text(strip=True) if empresa else ""
            ubicacion = card.select_one(SEL_UBICACION)
            ubicacion = ubicacion.get_text(strip=True) if ubicacion else ""
            fecha = card.select_one(SEL_FECHA)
            fecha = fecha.get_text(strip=True) if fecha else ""
            desc = card.select_one(SEL_DESC)
            desc = desc.get_text(strip=True) if desc else ""
            if not is_region_metropolitana(ubicacion):
                continue
            ofertas.append(
                self._make_oferta(titulo, empresa, ubicacion, fecha, desc, url, "laborum.com")
            )
        return ofertas

    def fetch(self) -> list[dict]:
        # laborum.com es una SPA React con API protegida (403 en endpoints internos).
        # Headless browsers son bloqueados activamente.
        # TODO: investigar API interna o alternativas de scraping.
        print("[laborum.com] Sitio bloquea automatización. Skipping.")
        return []
```

```python
# scrapers/trabajando.py
from bs4 import BeautifulSoup
from scrapers.base import KeywordSearchScraper, is_region_metropolitana
from scrapers.registry import register

BASE_URL = "https://www.trabajando.cl/trabajo/buscar"
REGION_PARAM = "Región Metropolitana"

SEL_CARD = "div.aviso-wrap"
SEL_TITULO = "h2.aviso-titulo a"
SEL_EMPRESA = "span.empresa-nombre"
SEL_UBICACION = "span.lugar"
SEL_FECHA = "span.fecha-publicacion"
SEL_DESC = "p.descripcion-corta"


@register("trabajando")
class TrabajandoScraper(KeywordSearchScraper):
    def _parse_html(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        ofertas = []
        for card in soup.select(SEL_CARD):
            titulo_tag = card.select_one(SEL_TITULO)
            if not titulo_tag:
                continue
            titulo = titulo_tag.get_text(strip=True)
            href = titulo_tag.get("href", "")
            url = f"https://www.trabajando.cl{href}" if href.startswith("/") else href
            empresa = card.select_one(SEL_EMPRESA)
            empresa = empresa.get_text(strip=True) if empresa else ""
            ubicacion = card.select_one(SEL_UBICACION)
            ubicacion = ubicacion.get_text(strip=True) if ubicacion else ""
            fecha = card.select_one(SEL_FECHA)
            fecha = fecha.get_text(strip=True) if fecha else ""
            desc = card.select_one(SEL_DESC)
            desc = desc.get_text(strip=True) if desc else ""
            if not is_region_metropolitana(ubicacion):
                continue
            ofertas.append(
                self._make_oferta(titulo, empresa, ubicacion, fecha, desc, url, "trabajando.cl")
            )
        return ofertas

    def fetch(self) -> list[dict]:
        # trabajando.cl es una SPA Nuxt que bloquea headless browsers.
        # El HTML estático no contiene datos de ofertas.
        # TODO: investigar API interna o alternativas de scraping.
        print("[trabajando.cl] Sitio bloquea automatización. Skipping.")
        return []
```

Both files drop the unused `import time`, `import requests`, and `from fake_useragent import UserAgent` from the originals (dead imports, never used in either file).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_laborum.py tests/test_trabajando.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add scrapers/laborum.py scrapers/trabajando.py tests/test_laborum.py tests/test_trabajando.py
git commit -m "refactor: parametrize Laborum/Trabajando keywords, register them, drop dead imports"
```

---

### Task 8: Generic PortalListScraper (replaces trabajando_portal.py)

**Files:**
- Create: `scrapers/portal_list.py`
- Create: `tests/test_portal_list.py`
- Create: `tests/fixtures/portal_list_sample.html` (copy of `tests/fixtures/trabajando_portal_sample.html`)
- Delete: `scrapers/trabajando_portal.py`
- Delete: `tests/test_trabajando_portal.py`
- Delete: `tests/fixtures/trabajando_portal_sample.html`

**Interfaces:**
- Consumes: `PortalListScraper.__init__(keywords, portales)` from Task 2.
- Produces: `PortalListScraper(keywords=[...], portales=[{"nombre", "base_url", "fuente"}, ...])`, registered as `"portal_list"`. `_parse_html(html, base_url, fuente)` — note the signature gained two params compared to the old `TrabajandoPortalScraper._parse_html(html)`, since one instance now iterates multiple portals instead of holding a single `base_url`/`fuente` pair.

This also fixes a latent bug: the original `trabajando_portal.py` imported `from playwright.sync_api import sync_playwright` at module level (unguarded), unlike `bne.py`/`indeed.py` which import it lazily inside `fetch()`. An unguarded top-level import means importing `scrapers` (and therefore `run.py`) crashes entirely if `playwright` isn't installed, even for profiles that don't use `portal_list`. This task moves the import inside `fetch()`, matching the other two scrapers.

- [ ] **Step 1: Copy the fixture and write the failing test**

```bash
cp tests/fixtures/trabajando_portal_sample.html tests/fixtures/portal_list_sample.html
```

```python
# tests/test_portal_list.py
from pathlib import Path
from scrapers.portal_list import PortalListScraper

FIXTURE = (Path(__file__).parent / "fixtures" / "portal_list_sample.html").read_text(encoding="utf-8")
BASE_URL = "https://clinicaalemana.trabajando.cl"
KEYWORDS = ["Químico", "Farmacéutico", "Regente Farmacia", "Bioquímico"]


def _make_scraper():
    return PortalListScraper(
        keywords=KEYWORDS,
        portales=[{"nombre": "clinicaalemana", "base_url": BASE_URL, "fuente": "clinicaalemana.cl"}],
    )


def test_parse_filtra_qf():
    scraper = _make_scraper()
    ofertas = scraper._parse_html(FIXTURE, BASE_URL, "clinicaalemana.cl")
    # fixture: 1 QF en RM, 1 no-QF RM excluido, 1 QF fuera RM excluido
    assert len(ofertas) == 1
    assert "Químico" in ofertas[0]["titulo"]


def test_parse_excluye_no_qf():
    scraper = _make_scraper()
    ofertas = scraper._parse_html(FIXTURE, BASE_URL, "clinicaalemana.cl")
    assert not any("Data Governance" in o["titulo"] for o in ofertas)


def test_parse_excluye_fuera_rm():
    scraper = _make_scraper()
    ofertas = scraper._parse_html(FIXTURE, BASE_URL, "clinicaalemana.cl")
    assert not any("Concepción" in o["ubicacion"] for o in ofertas)


def test_parse_estructura_oferta():
    scraper = _make_scraper()
    ofertas = scraper._parse_html(FIXTURE, BASE_URL, "clinicaalemana.cl")
    assert len(ofertas) > 0
    oferta = ofertas[0]
    assert set(oferta.keys()) == {
        "titulo", "empresa", "ubicacion", "fecha_publicacion", "descripcion", "url", "fuente"
    }
    assert oferta["fuente"] == "clinicaalemana.cl"
    assert oferta["url"] == BASE_URL + "/trabajo/6052722-quimico-a-farmaceutico-a"
    assert "Vitacura" in oferta["ubicacion"]
    assert oferta["fecha_publicacion"] == "Hace 3 días"


def test_scraper_guarda_lista_de_portales():
    scraper = _make_scraper()
    assert scraper.portales == [
        {"nombre": "clinicaalemana", "base_url": BASE_URL, "fuente": "clinicaalemana.cl"}
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_portal_list.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scrapers.portal_list'`.

- [ ] **Step 3: Write minimal implementation**

```python
# scrapers/portal_list.py
from bs4 import BeautifulSoup
from scrapers.base import PortalListScraper as _PortalListScraperBase, is_region_metropolitana
from scrapers.registry import register

SEL_CARD      = "div.result-box"
SEL_TITULO    = "h2 a"
SEL_EMPRESA   = "span.type"
SEL_UBICACION = "span.location"
SEL_FECHA     = "div.date"


@register("portal_list")
class PortalListScraper(_PortalListScraperBase):
    """
    Scraper genérico para portales que comparten el layout de trabajando.cl
    (corporativos o públicos). Cada institución en `self.portales` es un dict
    con `nombre`, `base_url`, `fuente`.
    """

    def _parse_html(self, html: str, base_url: str, fuente: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        ofertas = []
        for card in soup.select(SEL_CARD):
            titulo_el = card.select_one(SEL_TITULO)
            if not titulo_el:
                continue
            titulo = titulo_el.get_text(strip=True)
            if not any(kw.lower() in titulo.lower() for kw in self.keywords):
                continue
            href = titulo_el.get("href", "")
            url = base_url + href if href.startswith("/") else href
            empresa_el = card.select_one(SEL_EMPRESA)
            empresa = empresa_el.get_text(strip=True) if empresa_el else ""
            ubicacion_el = card.select_one(SEL_UBICACION)
            ubicacion = ubicacion_el.get_text(strip=True) if ubicacion_el else ""
            if not is_region_metropolitana(ubicacion):
                continue
            fecha_el = card.select_one(SEL_FECHA)
            fecha = fecha_el.get_text(strip=True) if fecha_el else ""
            ofertas.append(
                self._make_oferta(titulo, empresa, ubicacion, fecha, "", url, fuente)
            )
        return ofertas

    def fetch(self) -> list[dict]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("[portal_list] playwright no instalado. Ejecutar: playwright install chromium")
            return []

        ofertas = []
        for portal in self.portales:
            base_url = portal["base_url"].rstrip("/")
            fuente = portal["fuente"]
            list_url = base_url + "/trabajo-empleo/"
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(
                        headless=True,
                        args=["--disable-blink-features=AutomationControlled"],
                    )
                    ctx = browser.new_context(
                        viewport={"width": 1280, "height": 900},
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    )
                    page = ctx.new_page()
                    page.add_init_script(
                        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                    )
                    page.goto(list_url, wait_until="networkidle", timeout=30000)
                    html = page.content()
                    browser.close()
            except Exception as e:
                print(f"[{fuente}] Error al cargar página: {e}")
                continue
            ofertas.extend(self._parse_html(html, base_url, fuente))
        return ofertas
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_portal_list.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Delete the old module, test, and fixture**

```bash
git rm scrapers/trabajando_portal.py tests/test_trabajando_portal.py tests/fixtures/trabajando_portal_sample.html
```

- [ ] **Step 6: Run the full scraper test suite to confirm nothing references the deleted files**

Run: `pytest tests/ -v --ignore=tests/test_run.py -k "not test_run"`
Expected: PASS, no `ModuleNotFoundError` for `trabajando_portal`.

- [ ] **Step 7: Commit**

```bash
git add scrapers/portal_list.py tests/test_portal_list.py tests/fixtures/portal_list_sample.html
git commit -m "feat: generalize trabajando_portal.py into a config-driven PortalListScraper"
```

---

### Task 9: Delete the Ahumada scraper (nicho, not reusable across professions)

**Files:**
- Delete: `scrapers/ahumada.py`
- Delete: `tests/test_ahumada.py`
- Delete: `tests/fixtures/ahumada_sample.html`

Per the approved design, `ahumada.py` is a scraper for one specific pharmacy chain's careers page — it doesn't generalize to other professions and has no reusable pattern (unlike the corporate/public portals, which share a common layout via `PortalListScraper`).

- [ ] **Step 1: Delete the files**

```bash
git rm scrapers/ahumada.py tests/test_ahumada.py tests/fixtures/ahumada_sample.html
```

- [ ] **Step 2: Run the full scraper test suite to confirm nothing references it**

Run: `pytest tests/ -v --ignore=tests/test_run.py`
Expected: PASS, no `ModuleNotFoundError` for `ahumada`.

- [ ] **Step 3: Commit**

```bash
git commit -m "chore: remove Ahumada scraper (pharmacy-specific, not reusable across professions)"
```

---

### Task 10: Profile files

**Files:**
- Create: `profiles/qf.yaml`
- Create: `profiles/arquitecto.yaml`

**Interfaces:**
- Produces: two YAML files consumed by `cargar_perfil()`/`construir_scrapers()` in Task 13.

- [ ] **Step 1: Write the QF profile (preserves current behavior)**

```yaml
# profiles/qf.yaml
nombre: qf
keywords:
  - "Químico Farmacéutico"
  - "QF"
  - "Farmacéutico Regente"
  - "Bioquímico"
scrapers:
  - computrabajo
  - indeed
  - laborum
  - trabajando
  - empleospublicos
  - bne
  - portal_list:
      portales:
        - {nombre: "clinicaalemana", base_url: "https://clinicaalemana.trabajando.cl", fuente: "clinicaalemana.cl"}
        - {nombre: "bupa", base_url: "https://bupa.trabajando.cl", fuente: "bupa.cl"}
        - {nombre: "redsalud", base_url: "https://redsalud.trabajando.cl", fuente: "redsalud.cl"}
        - {nombre: "banmedica", base_url: "https://banmedica.trabajando.cl", fuente: "banmedica.cl"}
        - {nombre: "colmena", base_url: "https://colmena.trabajando.cl", fuente: "colmena.cl"}
        - {nombre: "clinicasantamaria", base_url: "https://clinicasantamaria.trabajando.cl", fuente: "clinicasantamaria.cl"}
        - {nombre: "salcobrand", base_url: "https://empresassb.trabajando.cl", fuente: "salcobrand.cl"}
```

- [ ] **Step 2: Write the Arquitecto profile**

```yaml
# profiles/arquitecto.yaml
nombre: arquitecto
keywords:
  - "Arquitecto"
  - "Arquitectura"
scrapers:
  - computrabajo
  - indeed
  - laborum
  - trabajando
  - empleospublicos
  - bne
```

- [ ] **Step 3: Validate both parse as YAML**

Run: `python -c "import yaml; print(yaml.safe_load(open('profiles/qf.yaml'))); print(yaml.safe_load(open('profiles/arquitecto.yaml')))"`
Expected: both dicts print without error, each with `nombre`, `keywords`, `scrapers` keys.

(If `PyYAML` isn't installed yet, `pip install PyYAML` first — it's added to `requirements-scraper.txt` in Task 14.)

- [ ] **Step 4: Commit**

```bash
git add profiles/qf.yaml profiles/arquitecto.yaml
git commit -m "feat: add QF and Arquitecto search profiles"
```

---

### Task 11: SQLite storage layer

**Files:**
- Create: `storage.py`
- Create: `tests/test_storage.py`

**Interfaces:**
- Produces: `init_db(path) -> None`, `guardar(ofertas: list[dict], path) -> int` (returns count of newly-inserted rows, never overwrites `estado`), `listar(path, estado: str | None = None) -> list[dict]`, `marcar(path, url: str, estado: str) -> bool` (returns whether a row was updated; raises `ValueError` for an invalid `estado`), `ESTADOS_VALIDOS: set[str]`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_storage.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_storage.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'storage'`.

- [ ] **Step 3: Write minimal implementation**

```python
# storage.py
import sqlite3
from pathlib import Path

ESTADOS_VALIDOS = {"nuevo", "aplicado", "duplicado", "descartado"}

_CAMPOS = ["titulo", "empresa", "ubicacion", "fecha_publicacion", "descripcion", "fuente"]


def init_db(path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ofertas (
            url TEXT PRIMARY KEY,
            titulo TEXT,
            empresa TEXT,
            ubicacion TEXT,
            fecha_publicacion TEXT,
            descripcion TEXT,
            fuente TEXT,
            estado TEXT NOT NULL DEFAULT 'nuevo',
            first_seen TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()
    conn.close()


def guardar(ofertas: list[dict], path) -> int:
    """Inserta solo ofertas nuevas por url. Nunca sobreescribe estado. Retorna cuántas nuevas."""
    init_db(path)
    conn = sqlite3.connect(path)
    nuevas = 0
    for o in ofertas:
        url = o.get("url", "")
        if not url:
            continue
        existe = conn.execute("SELECT 1 FROM ofertas WHERE url = ?", (url,)).fetchone()
        if existe:
            continue
        conn.execute(
            "INSERT INTO ofertas (url, titulo, empresa, ubicacion, fecha_publicacion, descripcion, fuente) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (url, *(o.get(campo, "") for campo in _CAMPOS)),
        )
        nuevas += 1
    conn.commit()
    conn.close()
    return nuevas


def listar(path, estado: str | None = None) -> list[dict]:
    init_db(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    if estado:
        rows = conn.execute(
            "SELECT * FROM ofertas WHERE estado = ? ORDER BY first_seen DESC", (estado,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM ofertas ORDER BY first_seen DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def marcar(path, url: str, estado: str) -> bool:
    if estado not in ESTADOS_VALIDOS:
        raise ValueError(f"Estado inválido: {estado!r}. Válidos: {sorted(ESTADOS_VALIDOS)}")
    init_db(path)
    conn = sqlite3.connect(path)
    cur = conn.execute("UPDATE ofertas SET estado = ? WHERE url = ?", (estado, url))
    conn.commit()
    actualizado = cur.rowcount > 0
    conn.close()
    return actualizado
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_storage.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add storage.py tests/test_storage.py
git commit -m "feat: add SQLite storage layer for offer tracking"
```

---

### Task 12: Matrix-themed CLI

**Files:**
- Create: `cli.py`
- Create: `tests/test_cli.py`

**Interfaces:**
- Consumes: `storage.listar`, `storage.marcar`, `storage.ESTADOS_VALIDOS` from Task 11.
- Produces: `main(argv: list[str] | None = None) -> int` (entry point, returns process exit code — 0 success, 1 on `mark` against an unknown URL).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_cli.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cli'`.

- [ ] **Step 3: Write minimal implementation**

```python
# cli.py
import argparse
import random
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.table import Table

import storage

console = Console()
_MATRIX_CHARS = "アイウエオカキクケコサシスセソ0123456789"


def _splash(duration: float = 1.0) -> None:
    width = console.width or 80
    frames = max(1, int(duration / 0.05))
    for _ in range(frames):
        line = "".join(
            random.choice(_MATRIX_CHARS) if random.random() > 0.7 else " "
            for _ in range(width)
        )
        console.print(line, style="bold green", markup=False)
        time.sleep(0.05)
    console.clear()


def _db_path(profile: str) -> Path:
    return Path("data") / f"{profile}.db"


def cmd_list(args) -> int:
    if not args.no_anim:
        _splash()
    filas = storage.listar(_db_path(args.profile), estado=args.status)
    table = Table(border_style="green", header_style="bold green")
    for col in ("titulo", "empresa", "ubicacion", "fuente", "estado", "url"):
        table.add_column(col)
    for f in filas:
        table.add_row(f["titulo"], f["empresa"], f["ubicacion"], f["fuente"], f["estado"], f["url"])
    console.print(table, style="green")
    return 0


def cmd_mark(args) -> int:
    if not args.no_anim:
        _splash(duration=0.4)
    ok = storage.marcar(_db_path(args.profile), args.url, args.estado)
    if not ok:
        console.print(f"[bold red]No se encontró ninguna oferta con url {args.url!r}[/bold red]")
        return 1
    console.print(f"[bold green]✓ Marcada como '{args.estado}': {args.url}[/bold green]")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py")
    sub = parser.add_subparsers(dest="comando", required=True)

    p_list = sub.add_parser("list")
    p_list.add_argument("--profile", required=True)
    p_list.add_argument("--status", default=None, choices=sorted(storage.ESTADOS_VALIDOS))
    p_list.add_argument("--no-anim", action="store_true")
    p_list.set_defaults(func=cmd_list)

    p_mark = sub.add_parser("mark")
    p_mark.add_argument("--profile", required=True)
    p_mark.add_argument("url")
    p_mark.add_argument("estado", choices=sorted(storage.ESTADOS_VALIDOS))
    p_mark.add_argument("--no-anim", action="store_true")
    p_mark.set_defaults(func=cmd_mark)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add cli.py tests/test_cli.py
git commit -m "feat: add Matrix-themed CLI for listing and marking offer status"
```

---

### Task 13: Rewrite run.py and scrapers/__init__.py around profiles + registry + storage

**Files:**
- Modify: `scrapers/__init__.py`
- Modify: `run.py`
- Modify: `tests/test_run.py`

**Interfaces:**
- Consumes: `scrapers.registry.get`, `storage.guardar`, each scraper's `__init__(keywords=...)` / `__init__(keywords=..., portales=...)`.
- Produces: `cargar_perfil(nombre: str) -> dict` (raises `FileNotFoundError` if the profile YAML doesn't exist), `construir_scrapers(perfil: dict) -> list` (resolves each entry in `perfil["scrapers"]` — a bare string or a single-key dict like `{"portal_list": {"portales": [...]}}` — against the registry), `consolidar(listas: list[list[dict]]) -> list[dict]` (unchanged from today), `main()` (CLI entry point via `--profile`).

- [ ] **Step 1: Update `scrapers/__init__.py` so importing the package registers every scraper**

```python
# scrapers/__init__.py
from . import (  # noqa: F401
    computrabajo,
    indeed,
    laborum,
    trabajando,
    empleospublicos,
    bne,
    portal_list,
)
```

- [ ] **Step 2: Write the failing test for run.py**

```python
# tests/test_run.py
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_run.py -v`
Expected: FAIL — `ImportError: cannot import name 'cargar_perfil' from 'run'`.

- [ ] **Step 4: Write minimal implementation**

```python
# run.py
import argparse
from pathlib import Path

import yaml

import scrapers  # noqa: F401 — importar el paquete dispara los @register de cada módulo
import storage
from scrapers import registry

PROFILES_DIR = Path(__file__).parent / "profiles"


def consolidar(listas: list[list[dict]]) -> list[dict]:
    """Une todas las listas y elimina duplicados por URL."""
    seen: set[str] = set()
    result = []
    for lista in listas:
        for oferta in lista:
            url = oferta.get("url", "")
            if url not in seen:
                seen.add(url)
                result.append(oferta)
    return result


def cargar_perfil(nombre: str) -> dict:
    path = PROFILES_DIR / f"{nombre}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Perfil no encontrado: {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def construir_scrapers(perfil: dict) -> list:
    keywords = perfil["keywords"]
    instancias = []
    for entry in perfil["scrapers"]:
        if isinstance(entry, str):
            nombre, config = entry, {}
        else:
            (nombre, config), = entry.items()
        cls = registry.get(nombre)
        if nombre == "portal_list":
            instancias.append(cls(keywords=keywords, portales=config["portales"]))
        else:
            instancias.append(cls(keywords=keywords))
    return instancias


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()

    perfil = cargar_perfil(args.profile)
    scrapers_instanciados = construir_scrapers(perfil)

    resultados = []
    for scraper in scrapers_instanciados:
        nombre = type(scraper).__name__.replace("Scraper", "").lower()
        try:
            ofertas = scraper.fetch()
            print(f"[{nombre}] {len(ofertas)} ofertas encontradas")
            resultados.append(ofertas)
        except Exception as e:
            print(f"[{nombre}] Error inesperado: {e}")
            resultados.append([])

    consolidadas = consolidar(resultados)
    db_path = Path("data") / f"{perfil['nombre']}.db"
    nuevas = storage.guardar(consolidadas, db_path)

    print("---")
    print(f"Total encontradas: {len(consolidadas)} | Nuevas en DB: {nuevas}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_run.py -v`
Expected: PASS (6 passed)

- [ ] **Step 6: Commit**

```bash
git add scrapers/__init__.py run.py tests/test_run.py
git commit -m "refactor: rewrite run.py around profiles, registry, and SQLite storage"
```

---

### Task 14: Delete web UI, Google Sheets code, personal files, and CI; update dependencies

**Files:**
- Delete: `index.html`, `css/`, `js/`
- Delete: `sheets_writer.py`
- Delete: `CV Jorge Rojas.pdf`, `CV Jorge Rojas.pdf:Zone.Identifier`
- Delete: `.github/workflows/scraper.yml` (and the `.github` directory if now empty)
- Delete: `output/` (old CSV output dir, replaced by `data/`)
- Modify: `requirements-scraper.txt`
- Modify: `.gitignore`

- [ ] **Step 1: Delete the web UI, Sheets writer, personal file, CI workflow, and old output dir**

```bash
git rm -r index.html css js sheets_writer.py "CV Jorge Rojas.pdf" "CV Jorge Rojas.pdf:Zone.Identifier" .github output
```

- [ ] **Step 2: Update `requirements-scraper.txt`**

```
requests==2.31.0
beautifulsoup4==4.12.3
lxml==5.2.1
playwright==1.44.0
responses==0.25.3
pytest==8.2.0
PyYAML==6.0.1
rich==13.7.1
```

(Removes `fake-useragent`, `gspread`, `google-auth` — none are used anywhere after Tasks 3–7 and this task. Adds `PyYAML` for profile loading and `rich` for the CLI.)

- [ ] **Step 3: Update `.gitignore`**

```
__pycache__/
.pytest_cache/
*.pyc
.venv/
data/
.env
credentials.json
service_account.json
```

(Replaces the old `output/` entry with `data/`, the new SQLite storage directory. Drops `service_account.json`/`credentials.json` relevance note — left in place since they're harmless generic ignores, not tied to Sheets specifically.)

- [ ] **Step 4: Confirm no remaining references to deleted modules**

Run: `grep -rn "sheets_writer\|gspread\|google.oauth2\|fake_useragent" --include="*.py" .`
Expected: no output.

- [ ] **Step 5: Commit**

```bash
git add requirements-scraper.txt .gitignore
git commit -m "chore: remove web UI, Google Sheets integration, CI workflow, and personal files"
```

---

### Task 15: Full verification pass

**Files:** none (verification only)

- [ ] **Step 1: Install dependencies in a clean virtualenv**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-scraper.txt PyYAML rich
```

- [ ] **Step 2: Run the entire test suite**

Run: `pytest -v`
Expected: all tests pass — registry, base, computrabajo, indeed, laborum, trabajando, empleospublicos, portal_list, storage, cli, run. Zero `ImportError`/`ModuleNotFoundError`.

- [ ] **Step 3: Confirm no stray references to removed files**

```bash
grep -rn "ahumada\|trabajando_portal\|guardar_sheet\|guardar_csv\|COLUMNAS" --include="*.py" .
```

Expected: no output.

- [ ] **Step 4: Sanity-check the profile-driven CLI end to end (no network — just wiring)**

```bash
python -c "
from run import cargar_perfil, construir_scrapers
perfil = cargar_perfil('arquitecto')
instancias = construir_scrapers(perfil)
print([type(i).__name__ for i in instancias])
"
```

Expected: prints a list of 6 scraper class names (Computrabajo, Indeed, Laborum, Trabajando, EmpleosPublicos, Bne), no errors.

- [ ] **Step 5: Verify the CLI runs against an empty DB without crashing**

```bash
python cli.py list --profile arquitecto --no-anim
```

Expected: prints an empty `rich` table (no rows), exit code 0.

- [ ] **Step 6: Final commit (if any stragglers were fixed during verification)**

```bash
git add -A
git commit -m "test: verify full suite green after repurpose to generic multi-profile scraper"
```
