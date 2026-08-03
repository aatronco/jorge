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
