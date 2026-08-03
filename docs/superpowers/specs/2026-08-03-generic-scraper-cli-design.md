# Repurpose: Scraper Genérico de Empleo + CLI de Tracking — Spec de Diseño

**Fecha:** 2026-08-03
**Proyecto:** jorge
**Objetivo:** Convertir el scraper de empleos (hoy específico para Químico Farmacéutico) en una herramienta genérica multi-perfil, sin interfaz web, con tracking de estado de postulaciones desde una CLI de terminal.

---

## Contexto

El repo nació como scraper de ofertas para Químico Farmacéutico (QF) en la Región Metropolitana, con Google Sheets como backend de estado (columna "estado" que el humano editaba a mano en la planilla). También existe una webapp (`index.html`/`css`/`js`) para autenticación y visualización que nunca se terminó de integrar al flujo real.

Ahora se necesita reutilizar la misma base para otras profesiones (caso concreto: un arquitecto buscando trabajo), sin depender de una interfaz web ni de Google Sheets. Se prioriza reducir el proyecto a lo esencial: scrapers + storage local + una CLI para marcar ofertas como aplicada/duplicada/descartada.

Quedan explícitamente fuera de este repurpose (fases futuras):
- Mejoras a scrapers analizando network requests sitio por sitio.
- Parseo de CV a formato estándar vía IA.
- Generación de resume ajustado por oferta (ej. vía markdown-resume).

---

## Estructura del proyecto (después del repurpose)

```
jorge/
├── profiles/
│   └── arquitecto.yaml
├── scrapers/
│   ├── __init__.py          ← importa todos los módulos para disparar @register
│   ├── registry.py          ← decorator @register(nombre) + dict global
│   ├── base.py              ← KeywordSearchScraper, PortalListScraper, is_region_metropolitana
│   ├── computrabajo.py
│   ├── indeed.py
│   ├── laborum.py
│   ├── trabajando.py
│   ├── empleospublicos.py
│   ├── bne.py
│   └── portal_list.py       ← reemplaza trabajando_portal.py (genérico, corporativo o público)
├── storage.py                ← SQLite: guardar ofertas, consultar, actualizar estado
├── cli.py                    ← comandos list / mark, tema Matrix
├── run.py                    ← punto de entrada: carga perfil, corre scrapers, guarda en storage
├── requirements-scraper.txt
└── tests/
    ├── fixtures/...
    ├── test_base.py
    ├── test_<scraper>.py     ← uno por scraper, sin cambios de fondo
    ├── test_portal_list.py   ← reemplaza test_trabajando_portal.py
    ├── test_storage.py       ← nuevo
    ├── test_cli.py           ← nuevo
    └── test_run.py           ← reescrito
```

Se elimina: `index.html`, `css/`, `js/`, `sheets_writer.py`, `scrapers/ahumada.py`, `scrapers/trabajando_portal.py` (reemplazado por `portal_list.py`), `CV Jorge Rojas.pdf` (+ `:Zone.Identifier`), `.github/workflows/scraper.yml`. Se quitan `gspread`/`google-auth` de `requirements-scraper.txt` y se agrega `PyYAML` y `rich` (tema Matrix de la CLI).

---

## Arquitectura

### Perfiles (`profiles/*.yaml`)

Un archivo por persona/rol. Ejemplo (`profiles/arquitecto.yaml`):

```yaml
nombre: arquitecto
keywords:
  - "Arquitecto"
  - "Arquitectura"
location_filter: "Región Metropolitana"
scrapers:
  - computrabajo
  - indeed
  - laborum
  - trabajando
  - empleospublicos
  - bne
  - portal_list:
      portales:
        - {nombre: "ejemplo_empresa", base_url: "https://ejemplo.trabajando.cl", fuente: "ejemplo.cl"}
```

`keywords` y `location_filter` reemplazan los valores hardcodeados que hoy viven en `BaseScraper.KEYWORDS` y en `_RM_KEYWORDS`/lógica de filtro de cada scraper. `location_filter` es el nombre de una región soportada por `is_region_metropolitana`-equivalente generalizado (a futuro puede haber más de una región; por ahora basta con mantener la lógica de RM parametrizada por nombre).

### Registro de scrapers (`scrapers/registry.py`)

```python
_REGISTRY: dict[str, type] = {}

def register(nombre):
    def deco(cls):
        _REGISTRY[nombre] = cls
        return cls
    return deco

def get(nombre):
    return _REGISTRY[nombre]
```

Cada scraper se auto-registra con `@register("computrabajo")` en su propio archivo. `run.py` importa el paquete `scrapers` (que importa cada módulo y dispara los decorators) y luego resuelve cada entrada de la lista `scrapers` del perfil contra el registro. Si un portal público no encaja en el patrón `portal_list`, se agrega un módulo nuevo con su propio `@register(...)` sin tocar `run.py` ni el registro central.

### Dos bases en `scrapers/base.py`

- **`KeywordSearchScraper`**: para sitios de búsqueda por keyword (Computrabajo, Indeed, Laborum, Trabajando, EmpleosPublicos, BNE). Constructor recibe `keywords: list[str]` y `location_filter: str`. `fetch()` sigue el mismo patrón actual (una request/página por keyword), pero usa `self.keywords`/`self.location_filter` en vez de constantes hardcodeadas.
- **`PortalListScraper`** (en `scrapers/portal_list.py`): generaliza el patrón de `trabajando_portal.py` — recibe `portales: list[dict]` (cada uno con `nombre`, `base_url`, `fuente`) y `keywords`, y aplica el mismo parsing Playwright a cada portal de la lista. Sirve tanto para portales corporativos (Clínica Alemana, Bupa, etc., si el perfil los necesita) como públicos que compartan el mismo layout `trabajando.cl`. Si un portal público tiene layout distinto, se escribe una clase nueva independiente (no se fuerza a encajar en `PortalListScraper`).

Ambas heredan de `BaseScraper` (que mantiene `_make_oferta` y pasa a exponer `is_region_metropolitana` parametrizable por `location_filter`).

### Storage (`storage.py`)

SQLite en un archivo por perfil: `data/<perfil>.db` (carpeta `data/` gitignorada, igual que hoy `output/`).

```python
def init_db(path) -> None: ...
def guardar(ofertas: list[dict], path) -> int:
    """Inserta solo ofertas nuevas por url. Nunca sobreescribe estado. Retorna cuántas nuevas."""
def listar(path, estado: str | None = None) -> list[dict]: ...
def marcar(path, url_o_id, estado: str) -> bool: ...
```

Tabla `ofertas`: `url TEXT PRIMARY KEY, titulo, empresa, ubicacion, fecha_publicacion, descripcion, fuente, estado DEFAULT 'nuevo', first_seen`.

Estados válidos: `nuevo`, `aplicado`, `duplicado`, `descartado`.

### CLI (`cli.py`)

Comandos directos (no interactivo), tema visual Matrix:

```bash
python cli.py list --profile arquitecto [--status nuevo]
python cli.py mark --profile arquitecto <url> aplicado|duplicado|descartado
```

- **Splash animation:** al iniciar cualquier comando, 1-2 segundos de lluvia de caracteres estilo `cmatrix` (columnas de caracteres verdes cayendo sobre fondo negro) antes de mostrar el resultado. Implementación simple con `rich.console` + `time.sleep` entre frames (loop manual dibujando columnas aleatorias), sin dependencia externa de `cmatrix` (no es instalable vía pip de forma confiable multiplataforma). Debe poder saltarse con `--no-anim` para scripting/tests.
- `list` imprime una tabla (`rich.table.Table`, estilo verde) con `titulo`, `empresa`, `ubicacion`, `fuente`, `estado`, `url`.
- `mark` actualiza el estado por URL exacta (si no matchea ninguna fila, error claro en consola, no falla silenciosamente), con una animación corta de confirmación (breve destello verde) al marcar.

### Punto de entrada (`run.py`)

```bash
python run.py --profile arquitecto
```

1. Carga `profiles/<nombre>.yaml`.
2. Resuelve cada entrada de `scrapers` contra el registro, instancia con la config del perfil (`keywords`/`location_filter` o `portales` según corresponda).
3. Corre `fetch()` de cada uno con el mismo try/except por scraper que existe hoy (un sitio caído no detiene el resto).
4. Consolida y deduplica por `url` (reutiliza `consolidar()` actual, sin cambios).
5. Guarda en `storage.py` (reemplaza la llamada a `guardar_sheet`).
6. Imprime resumen igual que hoy (por scraper + total + nuevas).

---

## Manejo de errores

- Igual que hoy: un scraper que falla se loggea y no aborta el run completo.
- `cli.py mark` sobre una URL inexistente: mensaje de error explícito, exit code distinto de 0, no crashea con traceback.
- Perfil YAML inválido o con un nombre de scraper no registrado: error claro al inicio de `run.py`, antes de intentar scrapear nada.

---

## Testing

- Los ~35 tests de scrapers existentes (fixtures HTML reales) se mantienen; se ajustan solo para instanciar los scrapers con `keywords`/`location_filter` de prueba en vez de depender de constantes de clase.
- `test_run.py` se reescribe contra el nuevo `run.py` (carga de perfil + registry + storage), reemplazando las referencias a `guardar_csv`/`COLUMNAS` que ya no existen.
- Tests nuevos: `test_storage.py` (usa `tmp_path` para la DB — mismo patrón que ya usa `test_run.py` hoy con CSVs), `test_cli.py` (invoca comandos contra una DB de prueba, valida output y exit codes).
- Sin CI (se elimina el workflow de GitHub Actions); los tests se corren localmente con `pytest`.

---

## Uso

```bash
pip install -r requirements-scraper.txt
playwright install chromium  # solo si el perfil usa portal_list o algún scraper con JS

python run.py --profile arquitecto
python cli.py list --profile arquitecto --status nuevo
python cli.py mark --profile arquitecto https://ejemplo.cl/oferta/123 aplicado
```

---

## Criterios de éxito

- `python run.py --profile <nombre>` funciona para al menos dos perfiles distintos (QF y arquitecto) sin tocar código, solo cambiando el YAML.
- Ningún scraper tiene keywords o filtro geográfico hardcodeado en el código — todo viene del perfil.
- `cli.py list`/`mark` operan sobre SQLite local, sin credenciales externas.
- Los 35+ tests de scrapers siguen pasando; `test_run.py` deja de estar roto; pytest corre limpio de punta a punta.
- El repo ya no contiene la webapp, el PDF personal, ni dependencias de Google Sheets.
