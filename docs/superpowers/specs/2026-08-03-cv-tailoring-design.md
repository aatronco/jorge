# CV Tailoring Pipeline — Spec de Diseño

**Fecha:** 2026-08-03
**Proyecto:** jorge
**Objetivo:** Dado un CV base y una oferta ya scrapeada, generar un resume ajustado (PDF) para esa oferta específica, usando IA para estructurar el CV una vez y para priorizar/resumir por oferta.

---

## Contexto

Esta es la etapa 3 (y motivación original) del repurpose del proyecto: el amigo arquitecto necesita un CV distinto para cada oferta a la que postula, ajustado a lo que pide esa oferta puntual. Las etapas anteriores (scraper genérico + CLI de tracking, luego el fix de laborum.cl/trabajando.cl) ya dejaron listo: perfiles YAML, ofertas guardadas en SQLite (`storage.py`) con toda la info (`titulo`, `descripcion`, `empresa`, `url`), y una CLI Matrix (`cli.py`) para navegar esas ofertas.

Esta etapa agrega: importar el CV real de la persona una sola vez (estructurado por IA a un formato estándar), y por cada oferta que le interese, generar un PDF ajustado a partir de ese CV base + los datos de la oferta.

---

## Decisiones de diseño (de la sesión de brainstorming)

- **Invocación:** subcomandos nuevos de `cli.py`, no un script aparte — mismo flujo que ya usa el resto de la herramienta.
- **CV base:** el usuario pega/guarda su CV actual como texto plano (`.txt`); un LLM lo estructura una sola vez al formato estándar. No se soporta extracción de PDF/Word en esta fase (se puede agregar después si hace falta).
- **Formato estándar:** el schema abierto [JSON Resume](https://jsonresume.org/) (`basics`, `work`, `education`, `skills`, etc.) — no un YAML propio. Es un estándar externo, bien documentado, con herramientas de render ya construidas alrededor.
- **Backend de IA:** integración real contra la API de Anthropic (paquete `anthropic`, variable de entorno `ANTHROPIC_API_KEY`) — no un flujo manual de copiar/pegar a un chat.
- **Alcance del ajuste por oferta:** la IA NO reescribe descripciones de experiencia ni inventa contenido. Solo (a) reordena/prioriza qué entradas de `work[]`/`skills[]` destacar primero, y (b) escribe un `basics.summary` nuevo específico para esa oferta. Cero riesgo de que la IA tergiverse logros o fechas reales.
- **Render final:** se integra con [`resumed`](https://github.com/rbardini/resumed) (CLI de Node.js para JSON Resume, MIT) + un theme (`jsonresume-theme-even`) para exportar a PDF. Esto es un prerequisito de sistema nuevo (Node.js + `npm install -g resumed jsonresume-theme-even puppeteer`), no instalable vía pip — se documenta y se verifica en runtime con un mensaje de error claro si falta, mismo patrón que ya usa el proyecto para dependencias opcionales (`playwright`, `botasaurus`).
- **Forma del comando:** un solo comando hace tailoring + render (no dos pasos separados) — más simple para el usuario final. El JSON intermedio (ya ajustado) igual se guarda en disco como side-effect, para poder inspeccionarlo/editarlo a mano si algo sale raro, sin que sea un paso obligatorio del flujo normal.

---

## Estructura del proyecto (agregado por esta etapa)

```
jorge/
├── cv.py                      ← nuevo: importar_cv, tailorear_cv, renderizar_cv
├── cli.py                     ← agrega subcomandos: cv import, cv tailor
├── data/
│   ├── <perfil>.db            (ya existe, de storage.py)
│   ├── <perfil>-cv.json       ← CV base estructurado (JSON Resume)
│   └── <perfil>-tailored/
│       ├── <id-oferta>.json   ← copia ajustada por oferta
│       └── <id-oferta>.pdf    ← resume final renderizado
└── tests/
    ├── test_cv.py             ← nuevo (mockea la API de Anthropic y `resumed`)
    └── fixtures/
        └── cv_ejemplo.txt     ← CV de prueba en texto plano
```

Todo vive bajo `data/`, que ya está en `.gitignore` (contiene datos personales — CVs reales no deben terminar en el repo). No se reintroduce `output/`: esa carpeta se eliminó junto con el CSV viejo en la etapa 1 y ya no está gitignorada.

---

## Arquitectura

### `cv.py`

```python
def importar_cv(texto: str, perfil: str) -> dict:
    """Llama a la API de Claude para estructurar `texto` como JSON Resume.
    Guarda el resultado en data/<perfil>-cv.json y lo retorna."""

def tailorear_cv(cv_base: dict, oferta: dict) -> dict:
    """Llama a Claude con cv_base + oferta (titulo/empresa/descripcion).
    Claude retorna (vía tool use): el orden priorizado de índices de
    work[]/skills[], y un basics.summary nuevo. Se aplica sobre una
    COPIA de cv_base — nunca se muta el original, nunca se agregan
    entradas ni se reescriben bullets existentes."""

def renderizar_cv(json_path: Path, output_path: Path) -> None:
    """subprocess: resumed export <json_path> -o <output_path> -t jsonresume-theme-even.
    Si `resumed` no está en el PATH, error claro con el comando de instalación."""
```

### CLI (`cli.py`)

```bash
python cli.py cv import mi-cv.txt --profile arquitecto
python cli.py cv tailor --profile arquitecto <url-de-la-oferta>
```

`cv tailor`:
1. Carga `data/<perfil>-cv.json` (si no existe: error claro pidiendo correr `cv import` primero).
2. Busca la oferta por `url` en `storage.listar(db_path)` (si no existe: error claro).
3. Llama `tailorear_cv(cv_base, oferta)`, guarda en `data/<perfil>-tailored/<id>.json`.
4. Llama `renderizar_cv(...)`, guarda en `data/<perfil>-tailored/<id>.pdf`.
5. Imprime la ruta del PDF generado.

`<id-oferta>` se deriva de un hash corto de la URL (mismo enfoque simple que ya usa el proyecto para claves — evita nombres de archivo con caracteres raros de una URL completa).

---

## Manejo de errores

- CV base no importado aún → error claro, sugiere correr `cv import` primero.
- Oferta no encontrada por URL en storage → error claro, no se llama a la IA (evita gasto innecesario de tokens).
- Respuesta de Claude que no matchea el schema esperado (tool use con schema inválido) → error explícito, no se guarda un JSON corrupto ni se intenta renderizar.
- `resumed` no instalado o no encontrado en el PATH → mensaje con el comando de instalación exacto (`npm install -g resumed jsonresume-theme-even puppeteer`), no un traceback crudo.
- Error de red/API de Anthropic → se loggea y se aborta ese comando (no hay fallback silencioso — a diferencia de los scrapers, aquí un fallo debe ser visible, no ocultarse como "0 resultados").

---

## Testing

- `tailorear_cv`: se mockea la llamada a la API de Anthropic (sin gastar tokens reales) y se verifica que (a) el CV base pasado nunca se muta, (b) el resultado tiene el mismo número de entradas en `work[]`/`skills[]` que el original (solo reordenadas, nunca agregadas/quitadas), y (c) `basics.summary` cambió.
- `importar_cv`: se mockea la respuesta de la API y se verifica que el JSON resultante tiene las claves top-level esperadas del schema JSON Resume.
- `renderizar_cv`: se mockea `subprocess.run` — se verifica que se llama con los argumentos correctos, sin correr Node.js real en la suite.
- No hay test end-to-end contra la API real de Anthropic ni contra `resumed` real (igual que los scrapers Playwright/Botasaurus no tienen test end-to-end contra los sitios reales) — se documenta que hay que probarlo manualmente con una `ANTHROPIC_API_KEY` real y `resumed` instalado.

---

## Uso

```bash
pip install anthropic          # se agrega a requirements-scraper.txt
npm install -g resumed jsonresume-theme-even puppeteer   # prerequisito de sistema, no vía pip

export ANTHROPIC_API_KEY=sk-...

python cli.py cv import mi-cv.txt --profile arquitecto
python cli.py cv tailor --profile arquitecto https://www.laborum.cl/empleos/arquitecto-de-aplicaciones-afp-habitat-s.a.-1118377676.html
# → data/arquitecto-tailored/<id>.pdf
```

---

## Criterios de éxito

- `cv import` produce un JSON Resume válido a partir de un CV en texto plano, guardado en `data/`.
- `cv tailor` produce un PDF en `data/<perfil>-tailored/` a partir de una oferta real guardada en SQLite, sin que la IA invente experiencia/fechas/logros que no estaban en el CV base.
- Ningún dato personal (CVs, tailored JSONs, PDFs) termina comiteado al repo — todo vive bajo `data/`/`output/`, ya gitignorados.
- Fallos (CV no importado, oferta no encontrada, `resumed` no instalado, error de API) dan mensajes claros, no tracebacks crudos.
