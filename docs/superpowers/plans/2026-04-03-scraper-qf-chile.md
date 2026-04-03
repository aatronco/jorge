# Scraper QF Chile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Script Python que raspa 4 portales de trabajo chilenos buscando "Químico Farmacéutico" y "QF" en la Región Metropolitana, y guarda resultados en un CSV acumulativo.

**Architecture:** Clase abstracta `BaseScraper` + función auxiliar `is_region_metropolitana`. Cuatro scrapers concretos (uno por sitio), cada uno con método `_parse_html` separado del HTTP para facilitar tests. `run.py` orquesta, deduplica por URL y persiste CSV. Indeed usa Playwright por JS. Los demás usan requests + BeautifulSoup.

**Tech Stack:** Python 3.10+, requests, beautifulsoup4, lxml, pandas, fake-useragent, playwright, pytest, responses

---

### Task 0: Setup del proyecto

**Files:**
- Create: `requirements.txt`
- Create: `scrapers/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/fixtures/` (directorio)
- Create: `output/.gitkeep`

- [ ] **Step 1: Crear estructura de carpetas**

```bash
mkdir -p scrapers tests/fixtures output
touch scrapers/__init__.py tests/__init__.py output/.gitkeep
```

- [ ] **Step 2: Crear `requirements.txt`**

```
requests==2.31.0
beautifulsoup4==4.12.3
lxml==5.2.1
pandas==2.2.2
fake-useragent==1.5.1
playwright==1.44.0
responses==0.25.3
pytest==8.2.0
```

- [ ] **Step 3: Instalar dependencias**

```bash
pip install -r requirements.txt
playwright install chromium
```

Expected: instalación exitosa sin errores de compatibilidad.

- [ ] **Step 4: Inicializar git**

```bash
git init
printf "output/ofertas_qf.csv\n__pycache__/\n.pytest_cache/\n*.pyc\n.venv/\n" > .gitignore
git add .
git commit -m "chore: project scaffolding"
```

---

### Task 1: BaseScraper y filtro geográfico

**Files:**
- Create: `scrapers/base.py`
- Create: `tests/test_base.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_base.py
import pytest
from scrapers.base import BaseScraper, is_region_metropolitana


def test_rm_keywords_positivos():
    assert is_region_metropolitana("Santiago") is True
    assert is_region_metropolitana("Providencia, Región Metropolitana") is True
    assert is_region_metropolitana("Las Condes, RM") is True
    assert is_region_metropolitana("Puente Alto") is True
    assert is_region_metropolitana("Maipú") is True
    assert is_region_metropolitana("San Bernardo") is True


def test_rm_keywords_negativos():
    assert is_region_metropolitana("Valparaíso") is False
    assert is_region_metropolitana("Concepción") is False
    assert is_region_metropolitana("Antofagasta") is False
    assert is_region_metropolitana("Temuco") is False
    assert is_region_metropolitana("La Serena") is False


def test_rm_sin_ubicacion_incluye():
    # Sin ubicación definida se incluye para revisión manual
    assert is_region_metropolitana("") is True
    assert is_region_metropolitana(None) is True


def test_base_scraper_es_abstracta():
    with pytest.raises(TypeError):
        BaseScraper()


def test_make_oferta_normaliza_none():
    class Concreto(BaseScraper):
        def fetch(self):
            return []

    scraper = Concreto()
    oferta = scraper._make_oferta(None, None, None, None, None, None, "test")
    for k, v in oferta.items():
        if k != "fuente":
            assert v == "", f"Campo '{k}' debería ser '' pero es {v!r}"
    assert oferta["fuente"] == "test"


def test_make_oferta_estructura_completa():
    class Concreto(BaseScraper):
        def fetch(self):
            return []

    scraper = Concreto()
    oferta = scraper._make_oferta("QF", "Lab", "Santiago", "2026-04-01", "desc", "https://x.cl", "fuente")
    assert set(oferta.keys()) == {
        "titulo", "empresa", "ubicacion", "fecha_publicacion", "descripcion", "url", "fuente"
    }
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

```bash
pytest tests/test_base.py -v
```

Expected: `ModuleNotFoundError: No module named 'scrapers.base'`

- [ ] **Step 3: Crear `scrapers/base.py`**

```python
# scrapers/base.py
from abc import ABC, abstractmethod

_RM_KEYWORDS = [
    "metropolitana", "santiago", " rm", "rm ", "providencia",
    "las condes", "ñuñoa", "maipú", "maipu", "la florida",
    "puente alto", "vitacura", "lo barnechea", "peñalolén", "penalolen",
    "macul", "san miguel", "estación central", "recoleta", "independencia",
    "quilicura", "pudahuel", "la pintana", "cerrillos", "el bosque",
    "san ramón", "la granja", "lo espejo", "pedro aguirre cerda",
    "san joaquín", "lo prado", "quinta normal", "cerro navia",
    "renca", "huechuraba", "conchalí", "colina", "lampa", "til til",
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
    KEYWORDS = ["Químico Farmacéutico", "QF"]

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
            "fuente": fuente,
        }
```

- [ ] **Step 4: Ejecutar el test y verificar que pasa**

```bash
pytest tests/test_base.py -v
```

Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add scrapers/base.py scrapers/__init__.py tests/test_base.py tests/__init__.py
git commit -m "feat: add BaseScraper with RM geo filter"
```

---

### Task 2: Scraper trabajando.com

**Files:**
- Create: `scrapers/trabajando.py`
- Create: `tests/test_trabajando.py`
- Create: `tests/fixtures/trabajando_sample.html`

**Nota importante:** Los selectores CSS en las constantes `SEL_*` son los más probables según la estructura típica del sitio. Antes del smoke test final (Task 7), verificar abriendo `https://www.trabajando.cl/trabajo/buscar?q=QF&r=Regi%C3%B3n+Metropolitana` en Chrome → Inspeccionar elemento → buscar el div que envuelve cada oferta.

- [ ] **Step 1: Crear fixture HTML**

```html
<!-- tests/fixtures/trabajando_sample.html -->
<!DOCTYPE html>
<html lang="es">
<body>
  <div class="listado-avisos">
    <div class="aviso-wrap">
      <h2 class="aviso-titulo">
        <a href="/trabajo/ver/12345">Químico Farmacéutico Regente</a>
      </h2>
      <span class="empresa-nombre">Farmacia Chile SpA</span>
      <span class="lugar">Santiago, Región Metropolitana</span>
      <span class="fecha-publicacion">hace 1 día</span>
      <p class="descripcion-corta">Se busca QF para regentear farmacia zona oriente.</p>
    </div>
    <div class="aviso-wrap">
      <h2 class="aviso-titulo">
        <a href="/trabajo/ver/67890">QF Control de Calidad</a>
      </h2>
      <span class="empresa-nombre">Lab Regional Sur</span>
      <span class="lugar">Valparaíso</span>
      <span class="fecha-publicacion">hace 3 días</span>
      <p class="descripcion-corta">Control de calidad en planta farmacéutica.</p>
    </div>
  </div>
</body>
</html>
```

- [ ] **Step 2: Escribir el test que falla**

```python
# tests/test_trabajando.py
from pathlib import Path
from scrapers.trabajando import TrabajandoScraper

FIXTURE = (Path(__file__).parent / "fixtures" / "trabajando_sample.html").read_text(encoding="utf-8")


def test_parse_filtra_rm():
    scraper = TrabajandoScraper()
    ofertas = scraper._parse_html(FIXTURE)

    assert len(ofertas) == 1
    assert "Farmacia Chile" in ofertas[0]["empresa"]
    assert "Santiago" in ofertas[0]["ubicacion"]


def test_parse_excluye_fuera_rm():
    scraper = TrabajandoScraper()
    ofertas = scraper._parse_html(FIXTURE)

    ubicaciones = [o["ubicacion"] for o in ofertas]
    assert not any("Valparaíso" in u for u in ubicaciones)


def test_parse_estructura_oferta():
    scraper = TrabajandoScraper()
    ofertas = scraper._parse_html(FIXTURE)

    assert len(ofertas) > 0
    oferta = ofertas[0]
    assert set(oferta.keys()) == {
        "titulo", "empresa", "ubicacion", "fecha_publicacion", "descripcion", "url", "fuente"
    }
    assert oferta["fuente"] == "trabajando.com"
    assert oferta["url"].startswith("https://www.trabajando.cl")
    assert oferta["titulo"] == "Químico Farmacéutico Regente"
```

- [ ] **Step 3: Ejecutar el test y verificar que falla**

```bash
pytest tests/test_trabajando.py -v
```

Expected: `ModuleNotFoundError: No module named 'scrapers.trabajando'`

- [ ] **Step 4: Crear `scrapers/trabajando.py`**

```python
# scrapers/trabajando.py
import time

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from scrapers.base import BaseScraper, is_region_metropolitana

BASE_URL = "https://www.trabajando.cl/trabajo/buscar"
REGION_PARAM = "Región Metropolitana"

# Si algún campo no se extrae, abrir la URL en Chrome e inspeccionar
# los elementos de cada tarjeta de oferta y actualizar estas constantes:
SEL_CARD = "div.aviso-wrap"
SEL_TITULO = "h2.aviso-titulo a"
SEL_EMPRESA = "span.empresa-nombre"
SEL_UBICACION = "span.lugar"
SEL_FECHA = "span.fecha-publicacion"
SEL_DESC = "p.descripcion-corta"


class TrabajandoScraper(BaseScraper):
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
                self._make_oferta(titulo, empresa, ubicacion, fecha, desc, url, "trabajando.com")
            )
        return ofertas

    def fetch(self) -> list[dict]:
        ua = UserAgent()
        headers = {"User-Agent": ua.random}
        ofertas = []

        for keyword in self.KEYWORDS:
            params = {"q": keyword, "r": REGION_PARAM}
            try:
                resp = requests.get(BASE_URL, params=params, headers=headers, timeout=15)
                resp.raise_for_status()
            except Exception as e:
                print(f"[trabajando.com] Error al buscar '{keyword}': {e}")
                continue

            ofertas.extend(self._parse_html(resp.text))
            time.sleep(1)

        return ofertas
```

- [ ] **Step 5: Ejecutar el test y verificar que pasa**

```bash
pytest tests/test_trabajando.py -v
```

Expected: `3 passed`

- [ ] **Step 6: Commit**

```bash
git add scrapers/trabajando.py tests/test_trabajando.py tests/fixtures/trabajando_sample.html
git commit -m "feat: add trabajando.com scraper"
```

---

### Task 3: Scraper computrabajo.cl

**Files:**
- Create: `scrapers/computrabajo.py`
- Create: `tests/test_computrabajo.py`
- Create: `tests/fixtures/computrabajo_sample.html`

**Nota:** URL de búsqueda: `https://cl.computrabajo.com/trabajo-de-qu%C3%ADmico-farmac%C3%A9utico?where=Regi%C3%B3n+Metropolitana`. Verificar selectores `SEL_*` inspeccionando la página.

- [ ] **Step 1: Crear fixture HTML**

```html
<!-- tests/fixtures/computrabajo_sample.html -->
<!DOCTYPE html>
<html lang="es">
<body>
  <ul class="list-offers">
    <li>
      <article class="box_offer">
        <h2>
          <a href="/ofertas-de-trabajo/quimico-farmaceutico-santiago-10928374">
            QF Aseguramiento de Calidad
          </a>
        </h2>
        <p class="it_co"><a href="#">Laboratorio Bagó Chile</a></p>
        <p class="it_localizacion"><span>Santiago</span></p>
        <p class="fc_base"><span class="tag fc_base">hace 2 días</span></p>
      </article>
    </li>
    <li>
      <article class="box_offer">
        <h2>
          <a href="/ofertas-de-trabajo/qf-concepcion-10928375">
            QF Regente Farmacia
          </a>
        </h2>
        <p class="it_co"><a href="#">Farmacia Regional Sur</a></p>
        <p class="it_localizacion"><span>Concepción</span></p>
        <p class="fc_base"><span class="tag fc_base">hace 5 días</span></p>
      </article>
    </li>
  </ul>
</body>
</html>
```

- [ ] **Step 2: Escribir el test que falla**

```python
# tests/test_computrabajo.py
from pathlib import Path
from scrapers.computrabajo import ComputrabajoScraper

FIXTURE = (Path(__file__).parent / "fixtures" / "computrabajo_sample.html").read_text(encoding="utf-8")


def test_parse_filtra_rm():
    scraper = ComputrabajoScraper()
    ofertas = scraper._parse_html(FIXTURE)

    assert len(ofertas) == 1
    assert "Bagó" in ofertas[0]["empresa"]
    assert "Santiago" in ofertas[0]["ubicacion"]


def test_parse_excluye_concepcion():
    scraper = ComputrabajoScraper()
    ofertas = scraper._parse_html(FIXTURE)

    assert not any("Concepción" in o["ubicacion"] for o in ofertas)


def test_parse_estructura_oferta():
    scraper = ComputrabajoScraper()
    ofertas = scraper._parse_html(FIXTURE)

    oferta = ofertas[0]
    assert set(oferta.keys()) == {
        "titulo", "empresa", "ubicacion", "fecha_publicacion", "descripcion", "url", "fuente"
    }
    assert oferta["fuente"] == "computrabajo.cl"
    assert "cl.computrabajo.com" in oferta["url"]
    assert oferta["titulo"] == "QF Aseguramiento de Calidad"
```

- [ ] **Step 3: Ejecutar el test y verificar que falla**

```bash
pytest tests/test_computrabajo.py -v
```

Expected: `ModuleNotFoundError: No module named 'scrapers.computrabajo'`

- [ ] **Step 4: Crear `scrapers/computrabajo.py`**

```python
# scrapers/computrabajo.py
import time

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from scrapers.base import BaseScraper, is_region_metropolitana

# Verificar en https://cl.computrabajo.com si los selectores cambian:
SEL_CARD = "article.box_offer"
SEL_TITULO = "h2 a"
SEL_EMPRESA = "p.it_co a"
SEL_UBICACION = "p.it_localizacion span"
SEL_FECHA = "p.fc_base span"

KEYWORD_SLUGS = {
    "Químico Farmacéutico": "qu%C3%ADmico-farmac%C3%A9utico",
    "QF": "qf",
}


class ComputrabajoScraper(BaseScraper):
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
        ua = UserAgent()
        headers = {"User-Agent": ua.random}
        ofertas = []

        for keyword, slug in KEYWORD_SLUGS.items():
            url = f"https://cl.computrabajo.com/trabajo-de-{slug}"
            params = {"where": "Región Metropolitana"}
            try:
                resp = requests.get(url, params=params, headers=headers, timeout=15)
                resp.raise_for_status()
            except Exception as e:
                print(f"[computrabajo.cl] Error al buscar '{keyword}': {e}")
                continue

            ofertas.extend(self._parse_html(resp.text))
            time.sleep(1)

        return ofertas
```

- [ ] **Step 5: Ejecutar el test y verificar que pasa**

```bash
pytest tests/test_computrabajo.py -v
```

Expected: `3 passed`

- [ ] **Step 6: Commit**

```bash
git add scrapers/computrabajo.py tests/test_computrabajo.py tests/fixtures/computrabajo_sample.html
git commit -m "feat: add computrabajo.cl scraper"
```

---

### Task 4: Scraper laborum.com

**Files:**
- Create: `scrapers/laborum.py`
- Create: `tests/test_laborum.py`
- Create: `tests/fixtures/laborum_sample.html`

**Nota:** URL de búsqueda: `https://www.laborum.cl/empleos?q=quimico+farmaceutico&l=Regi%C3%B3n+Metropolitana`. Verificar selectores `SEL_*`.

- [ ] **Step 1: Crear fixture HTML**

```html
<!-- tests/fixtures/laborum_sample.html -->
<!DOCTYPE html>
<html lang="es">
<body>
  <div class="aviso-list">
    <div class="aviso-item">
      <a class="titulo-aviso" href="/empleos/quimico-farmaceutico-23456">
        QF Industria Farmacéutica
      </a>
      <span class="empresa">Recalcine SA</span>
      <span class="localidad">Santiago, Región Metropolitana</span>
      <span class="fecha">01/04/2026</span>
      <p class="extracto">Oferta para QF en área de producción.</p>
    </div>
    <div class="aviso-item">
      <a class="titulo-aviso" href="/empleos/qf-farmacia-34567">
        QF Farmacia Comunitaria
      </a>
      <span class="empresa">Cadena Farmacias Sur</span>
      <span class="localidad">Talca, VII Región</span>
      <span class="fecha">30/03/2026</span>
      <p class="extracto">Regente para farmacia en Talca.</p>
    </div>
  </div>
</body>
</html>
```

- [ ] **Step 2: Escribir el test que falla**

```python
# tests/test_laborum.py
from pathlib import Path
from scrapers.laborum import LaborumScraper

FIXTURE = (Path(__file__).parent / "fixtures" / "laborum_sample.html").read_text(encoding="utf-8")


def test_parse_filtra_rm():
    scraper = LaborumScraper()
    ofertas = scraper._parse_html(FIXTURE)

    assert len(ofertas) == 1
    assert "Recalcine" in ofertas[0]["empresa"]
    assert "Santiago" in ofertas[0]["ubicacion"]


def test_parse_excluye_talca():
    scraper = LaborumScraper()
    ofertas = scraper._parse_html(FIXTURE)

    assert not any("Talca" in o["ubicacion"] for o in ofertas)


def test_parse_estructura_oferta():
    scraper = LaborumScraper()
    ofertas = scraper._parse_html(FIXTURE)

    oferta = ofertas[0]
    assert set(oferta.keys()) == {
        "titulo", "empresa", "ubicacion", "fecha_publicacion", "descripcion", "url", "fuente"
    }
    assert oferta["fuente"] == "laborum.com"
    assert oferta["url"].startswith("https://www.laborum.cl")
    assert "2026" in oferta["fecha_publicacion"]
```

- [ ] **Step 3: Ejecutar el test y verificar que falla**

```bash
pytest tests/test_laborum.py -v
```

Expected: `ModuleNotFoundError: No module named 'scrapers.laborum'`

- [ ] **Step 4: Crear `scrapers/laborum.py`**

```python
# scrapers/laborum.py
import time

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from scrapers.base import BaseScraper, is_region_metropolitana

BASE_URL = "https://www.laborum.cl/empleos"

# Verificar en https://www.laborum.cl si los selectores cambian:
SEL_CARD = "div.aviso-item"
SEL_TITULO = "a.titulo-aviso"
SEL_EMPRESA = "span.empresa"
SEL_UBICACION = "span.localidad"
SEL_FECHA = "span.fecha"
SEL_DESC = "p.extracto"


class LaborumScraper(BaseScraper):
    def _parse_html(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        ofertas = []
        for card in soup.select(SEL_CARD):
            titulo_tag = card.select_one(SEL_TITULO)
            if not titulo_tag:
                continue
            titulo = titulo_tag.get_text(strip=True)
            href = titulo_tag.get("href", "")
            url = f"https://www.laborum.cl{href}" if href.startswith("/") else href

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
        ua = UserAgent()
        headers = {"User-Agent": ua.random}
        ofertas = []

        for keyword in self.KEYWORDS:
            params = {"q": keyword, "l": "Región Metropolitana"}
            try:
                resp = requests.get(BASE_URL, params=params, headers=headers, timeout=15)
                resp.raise_for_status()
            except Exception as e:
                print(f"[laborum.com] Error al buscar '{keyword}': {e}")
                continue

            ofertas.extend(self._parse_html(resp.text))
            time.sleep(1)

        return ofertas
```

- [ ] **Step 5: Ejecutar el test y verificar que pasa**

```bash
pytest tests/test_laborum.py -v
```

Expected: `3 passed`

- [ ] **Step 6: Commit**

```bash
git add scrapers/laborum.py tests/test_laborum.py tests/fixtures/laborum_sample.html
git commit -m "feat: add laborum.com scraper"
```

---

### Task 5: Scraper indeed.cl (con Playwright)

**Files:**
- Create: `scrapers/indeed.py`
- Create: `tests/test_indeed.py`
- Create: `tests/fixtures/indeed_sample.html`

**Nota:** Indeed.cl usa JavaScript para renderizar resultados y tiene anti-scraping agresivo. Se usa Playwright en modo headless. Los selectores de Indeed cambian frecuentemente — si devuelve 0 resultados, correr `playwright codegen cl.indeed.com` para inspeccionar los selectores actuales.

- [ ] **Step 1: Crear fixture HTML**

```html
<!-- tests/fixtures/indeed_sample.html -->
<!DOCTYPE html>
<html lang="es">
<body>
  <ul class="jobsearch-ResultsList">
    <li>
      <div class="job_seen_beacon">
        <h2 class="jobTitle">
          <a href="/pagemap:Jobs-a1b2c3d4e5f6" id="job_a1b2c3d4e5f6">
            <span title="Químico Farmacéutico Senior">Químico Farmacéutico Senior</span>
          </a>
        </h2>
        <span class="companyName">Laboratorio Maver</span>
        <div class="companyLocation">Santiago, Región Metropolitana</div>
        <span class="date">Publicado hace 1 día</span>
      </div>
    </li>
    <li>
      <div class="job_seen_beacon">
        <h2 class="jobTitle">
          <a href="/pagemap:Jobs-e5f6g7h8i9j0" id="job_e5f6g7h8i9j0">
            <span title="QF Producción Farmacéutica">QF Producción Farmacéutica</span>
          </a>
        </h2>
        <span class="companyName">Farmasa Viña</span>
        <div class="companyLocation">Viña del Mar, Valparaíso</div>
        <span class="date">Publicado hace 3 días</span>
      </div>
    </li>
  </ul>
</body>
</html>
```

- [ ] **Step 2: Escribir el test que falla**

```python
# tests/test_indeed.py
from pathlib import Path
from scrapers.indeed import IndeedScraper

FIXTURE = (Path(__file__).parent / "fixtures" / "indeed_sample.html").read_text(encoding="utf-8")


def test_parse_filtra_rm():
    scraper = IndeedScraper()
    ofertas = scraper._parse_html(FIXTURE)

    assert len(ofertas) == 1
    assert "Maver" in ofertas[0]["empresa"]
    assert "Santiago" in ofertas[0]["ubicacion"]


def test_parse_excluye_vina():
    scraper = IndeedScraper()
    ofertas = scraper._parse_html(FIXTURE)

    assert not any("Viña" in o["ubicacion"] for o in ofertas)


def test_parse_estructura_oferta():
    scraper = IndeedScraper()
    ofertas = scraper._parse_html(FIXTURE)

    oferta = ofertas[0]
    assert set(oferta.keys()) == {
        "titulo", "empresa", "ubicacion", "fecha_publicacion", "descripcion", "url", "fuente"
    }
    assert oferta["fuente"] == "indeed.cl"
    assert "cl.indeed.com" in oferta["url"]
    assert oferta["titulo"] == "Químico Farmacéutico Senior"
```

- [ ] **Step 3: Ejecutar el test y verificar que falla**

```bash
pytest tests/test_indeed.py -v
```

Expected: `ModuleNotFoundError: No module named 'scrapers.indeed'`

- [ ] **Step 4: Crear `scrapers/indeed.py`**

```python
# scrapers/indeed.py
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, is_region_metropolitana

BASE_URL = "https://cl.indeed.com/jobs"

# Indeed cambia sus selectores frecuentemente.
# Si devuelve 0 resultados, correr: playwright codegen cl.indeed.com
# y buscar los elementos de las tarjetas de trabajo.
SEL_CARD = "div.job_seen_beacon"
SEL_TITULO = "h2.jobTitle span"
SEL_TITULO_LINK = "h2.jobTitle a"
SEL_EMPRESA = "span.companyName"
SEL_UBICACION = "div.companyLocation"
SEL_FECHA = "span.date"


class IndeedScraper(BaseScraper):
    def _parse_html(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        ofertas = []
        for card in soup.select(SEL_CARD):
            titulo_tag = card.select_one(SEL_TITULO)
            link_tag = card.select_one(SEL_TITULO_LINK)
            if not titulo_tag:
                continue
            titulo = titulo_tag.get_text(strip=True)
            href = link_tag.get("href", "") if link_tag else ""
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
            fecha = card.select_one(SEL_FECHA)
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

        ofertas = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers({"Accept-Language": "es-CL,es;q=0.9"})

            for keyword in self.KEYWORDS:
                try:
                    kw_encoded = keyword.replace(" ", "+")
                    url = f"{BASE_URL}?q={kw_encoded}&l=Regi%C3%B3n+Metropolitana%2C+Chile"
                    page.goto(url, timeout=20000)
                    page.wait_for_selector(SEL_CARD, timeout=10000)
                    html = page.content()
                    ofertas.extend(self._parse_html(html))
                except Exception as e:
                    print(f"[indeed.cl] Error al buscar '{keyword}': {e}")

            browser.close()
        return ofertas
```

- [ ] **Step 5: Ejecutar el test y verificar que pasa**

```bash
pytest tests/test_indeed.py -v
```

Expected: `3 passed`

- [ ] **Step 6: Commit**

```bash
git add scrapers/indeed.py tests/test_indeed.py tests/fixtures/indeed_sample.html
git commit -m "feat: add indeed.cl scraper with Playwright"
```

---

### Task 6: run.py — orquestador y CSV

**Files:**
- Create: `run.py`
- Create: `tests/test_run.py`

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_run.py
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
    guardar_csv([OFERTA_SANTIAGO], csv_path)  # misma oferta

    df = pd.read_csv(csv_path)
    assert len(df) == 1


def test_guardar_csv_columnas_ordenadas(tmp_path):
    csv_path = tmp_path / "test.csv"
    guardar_csv([OFERTA_SANTIAGO], csv_path)

    df = pd.read_csv(csv_path)
    assert list(df.columns) == COLUMNAS
```

- [ ] **Step 2: Ejecutar el test y verificar que falla**

```bash
pytest tests/test_run.py -v
```

Expected: `ModuleNotFoundError: No module named 'run'`

- [ ] **Step 3: Crear `run.py`**

```python
# run.py
from pathlib import Path

import pandas as pd

from scrapers.trabajando import TrabajandoScraper
from scrapers.computrabajo import ComputrabajoScraper
from scrapers.laborum import LaborumScraper
from scrapers.indeed import IndeedScraper

OUTPUT_PATH = Path("output/ofertas_qf.csv")

COLUMNAS = [
    "titulo", "empresa", "ubicacion", "fecha_publicacion",
    "descripcion", "url", "fuente",
]


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


def guardar_csv(ofertas: list[dict], path: Path = OUTPUT_PATH) -> None:
    """Guarda ofertas en CSV. Si el archivo existe, acumula sin duplicar por URL."""
    df_nuevo = pd.DataFrame(ofertas, columns=COLUMNAS)
    if path.exists():
        df_existente = pd.read_csv(path, dtype=str).fillna("")
        df_combined = pd.concat([df_existente, df_nuevo], ignore_index=True)
        df_combined = df_combined.drop_duplicates(subset=["url"], keep="first")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        df_combined = df_nuevo
    df_combined[COLUMNAS].to_csv(path, index=False, encoding="utf-8-sig")


def main() -> None:
    scrapers = [
        TrabajandoScraper(),
        ComputrabajoScraper(),
        LaborumScraper(),
        IndeedScraper(),
    ]

    resultados = []
    for scraper in scrapers:
        nombre = type(scraper).__name__.replace("Scraper", "").lower()
        try:
            ofertas = scraper.fetch()
            print(f"[{nombre}] {len(ofertas)} ofertas encontradas")
            resultados.append(ofertas)
        except Exception as e:
            print(f"[{nombre}] Error inesperado: {e}")
            resultados.append([])

    consolidadas = consolidar(resultados)

    total_antes = 0
    if OUTPUT_PATH.exists():
        total_antes = len(pd.read_csv(OUTPUT_PATH))

    guardar_csv(consolidadas)

    total_despues = len(pd.read_csv(OUTPUT_PATH))
    nuevas = total_despues - total_antes

    print("---")
    print(
        f"Total: {len(consolidadas)} ofertas | {nuevas} nuevas | "
        f"CSV actualizado: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Ejecutar el test y verificar que pasa**

```bash
pytest tests/test_run.py -v
```

Expected: `6 passed`

- [ ] **Step 5: Correr todos los tests**

```bash
pytest -v
```

Expected: todos los tests pasan (17+ passed, 0 failed)

- [ ] **Step 6: Commit**

```bash
git add run.py tests/test_run.py
git commit -m "feat: add run.py orchestrator with accumulative CSV"
```

---

### Task 7: Smoke test contra sitios reales

**Files:** ninguno (solo verificación manual)

- [ ] **Step 1: Ejecutar el scraper**

```bash
python run.py
```

Si algún scraper reporta 0 ofertas y debería tener resultados:

1. Abrir la URL de búsqueda del sitio en Chrome
2. Abrir DevTools → Elements
3. Hacer hover sobre una tarjeta de oferta y comparar el selector con la constante `SEL_CARD` del scraper
4. Actualizar el selector en el archivo correspondiente y volver a correr

- [ ] **Step 2: Verificar el CSV generado**

```bash
python -c "
import pandas as pd
df = pd.read_csv('output/ofertas_qf.csv')
print(f'Total ofertas: {len(df)}')
print(df[['titulo','empresa','ubicacion','fuente']].to_string())
"
```

Expected: tabla con filas que muestran cargos en Santiago/RM de al menos uno de los 4 sitios.

- [ ] **Step 3: Commit si se actualizaron selectores**

```bash
git add scrapers/
git commit -m "fix: update CSS selectors after smoke test verification"
```
