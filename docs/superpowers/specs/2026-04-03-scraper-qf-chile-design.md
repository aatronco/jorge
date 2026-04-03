# Scraper de Ofertas QF Chile — Spec de Diseño

**Fecha:** 2026-04-03  
**Proyecto:** jorge  
**Objetivo:** Recolectar ofertas de trabajo para Químico Farmacéutico en Chile desde múltiples portales, consolidarlas en un CSV actualizable ejecutado manualmente.

---

## Contexto

Un Químico Farmacéutico (QF) busca trabajo en Chile. El objetivo es automatizar la búsqueda en múltiples portales para no tener que revisar cada sitio manualmente. El script se ejecuta a demanda y produce un CSV con todas las ofertas encontradas.

---

## Estructura del proyecto

```
jorge/
├── scrapers/
│   ├── __init__.py
│   ├── base.py          ← clase abstracta BaseScraper
│   ├── trabajando.py
│   ├── laborum.py
│   ├── indeed.py
│   └── computrabajo.py
├── run.py               ← punto de entrada
├── requirements.txt
└── output/
    └── ofertas_qf.csv
```

---

## Arquitectura

### BaseScraper (`scrapers/base.py`)

Clase abstracta con interfaz común que todos los scrapers deben implementar:

```python
class BaseScraper:
    KEYWORDS = ["Químico Farmacéutico", "QF"]
    
    def fetch(self) -> list[dict]:
        """Retorna lista de ofertas en formato estándar."""
        raise NotImplementedError
```

Cada scraper concreto hereda `BaseScraper`, implementa `fetch()`, y retorna una lista de dicts con la estructura definida abajo.

### Punto de entrada (`run.py`)

1. Instancia cada scraper
2. Llama `fetch()` en secuencia (con manejo de errores por scraper)
3. Consolida resultados
4. Deduplica por campo `url`
5. Guarda en `output/ofertas_qf.csv`
6. Imprime resumen: cuántas ofertas nuevas/totales por fuente

---

## Filtro geográfico

Solo se incluyen ofertas de la **Región Metropolitana** (Santiago y comunas aledañas). Cada scraper aplica el filtro de dos formas, según lo permita el sitio:

1. **Por parámetro de búsqueda** — se pasa `ubicacion=Santiago` o equivalente en la URL del portal.
2. **Por post-filtro** — si el portal no soporta filtro geográfico en la URL, se descarta toda oferta cuyo campo `ubicacion` no mencione "Metropolitana", "Santiago", "RM" o una comuna conocida de la RM.

Ofertas sin ubicación definida se incluyen con `ubicacion = ""` para revisión manual.

---

## Estructura de datos

Cada oferta es un `dict` con las siguientes claves:

| Campo | Tipo | Descripción |
|---|---|---|
| `titulo` | str | Título del cargo |
| `empresa` | str | Nombre de la empresa |
| `ubicacion` | str | Ciudad o región |
| `fecha_publicacion` | str | Fecha de publicación (ISO 8601 si disponible) |
| `descripcion` | str | Descripción breve del cargo |
| `url` | str | URL directa a la oferta |
| `fuente` | str | Nombre del sitio de origen |

Campos vacíos se guardan como string vacío `""`, no como `None`.

---

## Sitios — Fase 1

Los 4 portales de mayor volumen y relevancia para QF en Chile:

| Sitio | URL base de búsqueda | Método |
|---|---|---|
| trabajando.com | `https://www.trabajando.cl/trabajo/buscar?q=...` | requests + BS4 |
| laborum.com | `https://www.laborum.cl/empleos?q=...` | requests + BS4 |
| indeed.cl | `https://cl.indeed.com/jobs?q=...` | requests + BS4 |
| computrabajo.cl | `https://cl.computrabajo.com/trabajo-de-...` | requests + BS4 |

Si algún sitio requiere JavaScript para renderizar resultados, se usa `playwright` como fallback para ese scraper específico.

---

## Sitios — Fase 2 (futuro)

- Portales de farmacias: Cruz Verde, Salcobrand, Ahumada, Similares/Dr. Simi
- Empleo público: `empleos.gob.cl` o ChileAtiende
- Bolsas universitarias (UCh, PUC, USM, etc.)
- Clínicas privadas (Alemana, Bupa, UC Christus, etc.)

---

## Stack técnico

| Librería | Uso |
|---|---|
| `requests` | HTTP para sitios estáticos |
| `beautifulsoup4` | Parseo de HTML |
| `playwright` | Fallback para sitios con JS |
| `pandas` | Manejo y exportación del CSV |
| `fake_useragent` | Rotación de User-Agent para evitar bloqueos básicos |

---

## Comportamiento del CSV

- Si `output/ofertas_qf.csv` no existe, se crea desde cero.
- Si existe, se carga, se agregan las ofertas nuevas (deduplicando por `url`), y se sobreescribe.
- El CSV mantiene historial acumulativo entre ejecuciones.

---

## Manejo de errores

- Si un scraper falla (timeout, cambio de estructura del sitio, bloqueo), se registra el error en consola y se continúa con los demás scrapers.
- El script nunca aborta completamente por el fallo de un sitio.

---

## Uso

```bash
# Instalar dependencias
pip install -r requirements.txt
playwright install chromium  # solo si se necesita

# Ejecutar
python run.py
```

Salida esperada en consola:
```
[trabajando.com] 12 ofertas encontradas
[laborum.com]    8 ofertas encontradas
[indeed.cl]      15 ofertas encontradas
[computrabajo.cl] 6 ofertas encontradas
---
Total: 41 ofertas | 3 duplicadas removidas | CSV actualizado: output/ofertas_qf.csv
```

---

## Criterios de éxito

- El script corre sin errores en al menos 3 de los 4 sitios de Fase 1.
- El CSV resultante tiene todas las columnas definidas sin valores `None`.
- Las ofertas de diferentes fuentes con la misma URL no se duplican.
- Un sitio caído no detiene el resto del scraping.
