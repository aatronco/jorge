from scrapers.trabajando import TrabajandoScraper
from scrapers.computrabajo import ComputrabajoScraper
from scrapers.laborum import LaborumScraper
from scrapers.indeed import IndeedScraper
from scrapers.empleospublicos import EmpleosPublicosScraper
from scrapers.ahumada import AhumadaScraper
from scrapers.trabajando_portal import TrabajandoPortalScraper, PORTALES
from sheets_writer import guardar_sheet


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


def main() -> None:
    scrapers = [
        TrabajandoScraper(),
        ComputrabajoScraper(),
        LaborumScraper(),
        IndeedScraper(),
        EmpleosPublicosScraper(),
        AhumadaScraper(),
        *[TrabajandoPortalScraper(base_url, fuente) for _, (base_url, fuente) in PORTALES.items()],
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
    nuevas = guardar_sheet(consolidadas)

    print("---")
    print(f"Total encontradas: {len(consolidadas)} | Nuevas en sheet: {nuevas}")


if __name__ == "__main__":
    main()
