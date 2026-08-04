# CV Tailoring Pipeline — Spec de Diseño

**Fecha:** 2026-08-03
**Proyecto:** jorge
**Objetivo:** Dado un CV base y una oferta ya scrapeada, generar un resume ajustado (PDF) para esa oferta específica, usando IA para estructurar el CV una vez y para priorizar/resumir por oferta.

> **Nota (2026-08-03, revisión posterior):** la versión original de este spec integraba la API de Anthropic directamente (`anthropic.Anthropic()`, `ANTHROPIC_API_KEY`). Eso quedó descartado — el usuario no tiene cuenta/API key de Anthropic y en su lugar quiere que **Claude Code** (esta misma conversación) haga el razonamiento de IA directamente: leer el CV y estructurarlo, leer la oferta y decidir el orden + resumen. El código deja de llamar a ninguna API; solo hace las partes mecánicas y deterministas (guardar JSON, reordenar sin perder contenido, renderizar el PDF). Las secciones de abajo reflejan esta versión actualizada.

---

## Contexto

Esta es la etapa 3 (y motivación original) del repurpose del proyecto: el amigo arquitecto necesita un CV distinto para cada oferta a la que postula, ajustado a lo que pide esa oferta puntual. Las etapas anteriores (scraper genérico + CLI de tracking, luego el fix de laborum.cl/trabajando.cl) ya dejaron listo: perfiles YAML, ofertas guardadas en SQLite (`storage.py`) con toda la info (`titulo`, `descripcion`, `empresa`, `url`), y una CLI Matrix (`cli.py`) para navegar esas ofertas.

Esta etapa agrega: importar el CV real de la persona una sola vez (estructurado por IA a un formato estándar), y por cada oferta que le interese, generar un PDF ajustado a partir de ese CV base + los datos de la oferta.

---

## Decisiones de diseño (de la sesión de brainstorming)

- **Invocación:** subcomandos nuevos de `cli.py`, no un script aparte — mismo flujo que ya usa el resto de la herramienta.
- **CV base:** el usuario pega/guarda su CV actual como texto plano; Claude Code lo lee y lo estructura al formato estándar directamente en la conversación (sin llamar a ninguna API). No se soporta extracción de PDF/Word en esta fase (se puede agregar después si hace falta).
- **Formato estándar:** el schema abierto [JSON Resume](https://jsonresume.org/) (`basics`, `work`, `education`, `skills`, etc.) — no un YAML propio. Es un estándar externo, bien documentado, con herramientas de render ya construidas alrededor.
- **Backend de IA:** Claude Code (esta misma conversación) hace el razonamiento — no hay integración con la API de Anthropic ni ninguna otra API externa, ni variable de entorno de credenciales. El código (`cv.py`) solo recibe el resultado ya razonado (el CV estructurado, o el orden + resumen de un tailoring) como argumentos de función / de CLI, y hace las partes deterministas.
- **Alcance del ajuste por oferta:** la IA (Claude Code) NO reescribe descripciones de experiencia ni inventa contenido. Solo (a) decide el orden en que deberían aparecer las entradas de `work[]`/`skills[]`, y (b) escribe un `basics.summary` nuevo específico para esa oferta. El código aplica ese orden de forma determinista (`_aplicar_orden`), garantizando que nunca se pierda ni se agregue una entrada — cero riesgo de que se tergiversen logros o fechas reales, incluso si el razonamiento de la IA fuera descuidado.
- **Render final:** se integra con [`resumed`](https://github.com/rbardini/resumed) (CLI de Node.js para JSON Resume, MIT) + un theme (`jsonresume-theme-even`) para exportar a PDF. Esto es un prerequisito de sistema nuevo (Node.js + `npm install -g resumed jsonresume-theme-even puppeteer`), no instalable vía pip — se documenta y se verifica en runtime con un mensaje de error claro si falta, mismo patrón que ya usa el proyecto para dependencias opcionales (`playwright`, `botasaurus`).
- **Forma del comando:** un solo comando hace tailoring + render (no dos pasos separados) — más simple para el usuario final. El JSON intermedio (ya ajustado) igual se guarda en disco como side-effect, para poder inspeccionarlo/editarlo a mano si algo sale raro, sin que sea un paso obligatorio del flujo normal.

---

## Estructura del proyecto (agregado por esta etapa)

```
jorge/
├── cv.py                      ← nuevo: guardar_cv, aplicar_tailoring, renderizar_cv, id_oferta
├── cli.py                     ← agrega subcomandos: cv save, cv show-offer, cv tailor
├── data/
│   ├── <perfil>.db            (ya existe, de storage.py)
│   ├── <perfil>-cv.json       ← CV base estructurado (JSON Resume)
│   └── <perfil>-tailored/
│       ├── <id-oferta>.json   ← copia ajustada por oferta
│       └── <id-oferta>.pdf    ← resume final renderizado
└── tests/
    └── test_cv.py             ← nuevo (mockea solo `subprocess`/`resumed` — nada llama a una API)
```

Todo vive bajo `data/`, que ya está en `.gitignore` (contiene datos personales — CVs reales no deben terminar en el repo). No se reintroduce `output/`: esa carpeta se eliminó junto con el CSV viejo en la etapa 1 y ya no está gitignorada.

---

## Arquitectura

### `cv.py`

```python
def guardar_cv(cv_data: dict, perfil: str) -> None:
    """Guarda un CV ya estructurado (por Claude Code, en la conversación) en
    data/<perfil>-cv.json. Valida que tenga las claves top-level requeridas
    por CV_SCHEMA antes de escribir — nunca persiste un CV incompleto."""

def aplicar_tailoring(cv_base: dict, orden_work: list, orden_skills: list, summary: str) -> dict:
    """Aplica sobre una COPIA de cv_base el orden de work[]/skills[] y el
    resumen nuevo — ya decididos por Claude Code, no por una API. Nunca muta
    cv_base, nunca agrega/quita entradas (solo reordena, vía _aplicar_orden)."""

def renderizar_cv(json_path: Path, output_path: Path) -> None:
    """subprocess: resumed export <json_path> -o <output_path> -t jsonresume-theme-even.
    Si `resumed` no está en el PATH, error claro con el comando de instalación."""
```

### CLI (`cli.py`)

```bash
python cli.py cv save cv-estructurado.json --profile arquitecto
python cli.py cv show-offer --profile arquitecto <url-de-la-oferta>
python cli.py cv tailor --profile arquitecto <url-de-la-oferta> \
    --summary "..." --orden-work "1,0,2" --orden-skills "0,2,1"
```

Flujo típico de uso (con Claude Code haciendo el razonamiento entre pasos):
1. El usuario le pide a Claude Code "importa este CV" (adjunta/apunta a un `.txt`). Claude Code lo lee, lo estructura como JSON Resume, y lo guarda con `cli.py cv save <archivo.json> --profile X`.
2. El usuario le pide "genera el CV ajustado para esta oferta: `<url>`". Claude Code corre `cli.py cv show-offer --profile X <url>` para leer el título/descripción, razona el orden de relevancia y escribe un resumen, y corre `cli.py cv tailor --profile X <url> --summary "..." --orden-work "..." --orden-skills "..."`.

`cv tailor`:
1. Carga `data/<perfil>-cv.json` (si no existe: error claro pidiendo correr `cv save` primero).
2. Busca la oferta por `url` en `storage.obtener_por_url(db_path, url)` (si no existe: error claro).
3. Parsea `--orden-work`/`--orden-skills` (listas de índices separadas por coma), llama `aplicar_tailoring(cv_base, orden_work, orden_skills, summary)`, guarda en `data/<perfil>-tailored/<id>.json`.
4. Llama `renderizar_cv(...)`, guarda en `data/<perfil>-tailored/<id>.pdf`.
5. Imprime la ruta del PDF generado.

`<id-oferta>` se deriva de un hash corto de la URL (mismo enfoque simple que ya usa el proyecto para claves — evita nombres de archivo con caracteres raros de una URL completa).

---

## Manejo de errores

- CV base no guardado aún → error claro, sugiere correr `cv save` primero.
- Oferta no encontrada por URL en storage → error claro.
- CV pasado a `cv save` que no matchea el schema esperado (le faltan claves top-level) → error explícito, no se guarda un JSON corrupto ni se intenta renderizar.
- `--orden-work`/`--orden-skills` con un valor no numérico → error claro, no un traceback.
- `resumed` no instalado o no encontrado en el PATH → mensaje con el comando de instalación exacto (`npm install -g resumed jsonresume-theme-even puppeteer`), no un traceback crudo.
- Archivo no encontrado / JSON inválido al leer un archivo con `cv save` → error claro, no un traceback.

---

## Testing

- `aplicar_tailoring`: se verifica que (a) el CV base pasado nunca se muta, (b) no comparte referencias anidadas con el resultado (mutar el resultado no afecta al original), (c) el resultado tiene el mismo número de entradas en `work[]`/`skills[]` que el original (solo reordenadas, nunca agregadas/quitadas), y (d) `basics.summary` cambió.
- `guardar_cv`: se verifica que el JSON se escribe correctamente, y que un CV sin alguna clave top-level requerida lanza `ValueError` y no escribe archivo.
- `renderizar_cv`: se mockea `subprocess.run` — se verifica que se llama con los argumentos correctos, sin correr Node.js real en la suite.
- No hay ninguna llamada a una API externa en ningún test — el único proceso externo (`resumed`) está mockeado. No hay test end-to-end contra `resumed` real (igual que los scrapers Playwright/Botasaurus no tienen test end-to-end contra los sitios reales) — se documenta que hay que probarlo manualmente con `resumed`/`puppeteer` instalados.

---

## Uso

```bash
npm install -g resumed jsonresume-theme-even puppeteer   # prerequisito de sistema, no vía pip

# 1. Pídele a Claude Code que importe el CV (lee el .txt, lo estructura, y guarda):
python cli.py cv save cv-estructurado.json --profile arquitecto

# 2. Pídele a Claude Code que genere el CV ajustado para una oferta puntual
#    (Claude Code corre esto internamente tras leer la oferta y razonar el tailoring):
python cli.py cv show-offer --profile arquitecto <url-de-la-oferta>
python cli.py cv tailor --profile arquitecto <url-de-la-oferta> \
    --summary "..." --orden-work "1,0,2" --orden-skills "0,2,1"
# → data/arquitecto-tailored/<id>.pdf
```

---

## Criterios de éxito

- `cv save` persiste un JSON Resume válido (ya estructurado por Claude Code) en `data/`, rechazando cualquier CV incompleto.
- `cv tailor` produce un PDF en `data/<perfil>-tailored/` a partir de una oferta real guardada en SQLite, sin que el código invente ni pierda experiencia/fechas/logros que no estaban en el CV base — la garantía la da `_aplicar_orden`, no la IA.
- Ningún dato personal (CVs, tailored JSONs, PDFs) termina comiteado al repo — todo vive bajo `data/`, ya gitignorado.
- Fallos (CV no guardado, oferta no encontrada, orden inválido, `resumed` no instalado) dan mensajes claros, no tracebacks crudos.
- Cero dependencia de una API key o cuenta de terceros — todo el razonamiento de IA lo hace Claude Code en la conversación.
