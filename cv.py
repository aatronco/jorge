import json
from pathlib import Path

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
