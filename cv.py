import hashlib
import json
import subprocess
from pathlib import Path

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


def guardar_cv(cv_data: dict, perfil: str) -> None:
    """Guarda un CV ya estructurado en formato JSON Resume (por Claude Code,
    en la conversación) en data/<perfil>-cv.json. Valida que tenga las claves
    top-level requeridas por CV_SCHEMA antes de escribir — nunca persiste un
    CV incompleto."""
    faltantes = [clave for clave in CV_SCHEMA["required"] if clave not in cv_data]
    if faltantes:
        raise ValueError(f"El CV no tiene el formato esperado — faltan las claves: {faltantes}")
    path = Path("data") / f"{perfil}-cv.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cv_data, ensure_ascii=False, indent=2), encoding="utf-8")


def aplicar_tailoring(cv_base: dict, orden_work: list, orden_skills: list, summary: str) -> dict:
    """Aplica sobre una COPIA de cv_base el reordenamiento de work[]/skills[]
    y el resumen nuevo — ya decididos por Claude Code en la conversación, no
    por una llamada a una API. Nunca muta cv_base, nunca agrega/quita
    entradas (solo reordena, vía _aplicar_orden)."""
    tailored = json.loads(json.dumps(cv_base))  # copia profunda, nunca muta cv_base
    tailored["work"] = _aplicar_orden(tailored.get("work", []), orden_work)
    tailored["skills"] = _aplicar_orden(tailored.get("skills", []), orden_skills)
    tailored.setdefault("basics", {})["summary"] = summary
    return tailored


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
            "'resumed' no está instalado. Ejecutar: npm install -g resumed jsonresume-theme-even puppeteer"
        )
    except subprocess.CalledProcessError as e:
        detalle = e.stderr.decode(errors="replace") if e.stderr else str(e)
        raise RuntimeError(f"resumed falló al exportar el PDF: {detalle}")
