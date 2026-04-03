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
    KEYWORDS = ("Químico Farmacéutico", "QF")

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
