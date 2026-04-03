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
