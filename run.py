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
