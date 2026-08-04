import argparse
import json
import random
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.table import Table

import cv
import storage

console = Console()
_MATRIX_CHARS = "アイウエオカキクケコサシスセソ0123456789"


def _splash(duration: float = 1.0) -> None:
    width = console.width or 80
    frames = max(1, int(duration / 0.05))
    for _ in range(frames):
        line = "".join(
            random.choice(_MATRIX_CHARS) if random.random() > 0.7 else " "
            for _ in range(width)
        )
        console.print(line, style="bold green", markup=False)
        time.sleep(0.05)
    console.clear()


def _db_path(profile: str) -> Path:
    return Path("data") / f"{profile}.db"


def cmd_list(args) -> int:
    if not args.no_anim:
        _splash()
    filas = storage.listar(_db_path(args.profile), estado=args.status)
    table = Table(border_style="green", header_style="bold green")
    for col in ("titulo", "empresa", "ubicacion", "fuente", "estado", "url"):
        table.add_column(col)
    for f in filas:
        table.add_row(f["titulo"], f["empresa"], f["ubicacion"], f["fuente"], f["estado"], f["url"])
    console.print(table, style="green")
    return 0


def cmd_mark(args) -> int:
    if not args.no_anim:
        _splash(duration=0.4)
    ok = storage.marcar(_db_path(args.profile), args.url, args.estado)
    if not ok:
        console.print(f"[bold red]No se encontró ninguna oferta con url {args.url!r}[/bold red]")
        return 1
    console.print(f"[bold green]✓ Marcada como '{args.estado}': {args.url}[/bold green]")
    return 0


def cmd_cv_save(args) -> int:
    """Guarda un CV que Claude Code ya estructuró como JSON Resume durante la
    conversación (no llama a ninguna API — el razonamiento ya está hecho)."""
    try:
        cv_data = json.loads(Path(args.archivo).read_text(encoding="utf-8"))
    except (FileNotFoundError, UnicodeDecodeError, OSError, json.JSONDecodeError) as e:
        console.print(f"[bold red]No se pudo leer el archivo {args.archivo!r}: {e}[/bold red]")
        return 1
    try:
        cv.guardar_cv(cv_data, args.profile)
    except ValueError as e:
        console.print(f"[bold red]{e}[/bold red]")
        return 1
    console.print(f"[bold green]✓ CV guardado para el perfil '{args.profile}'[/bold green]")
    return 0


def cmd_cv_show_offer(args) -> int:
    """Imprime los datos de una oferta guardada, para que Claude Code los lea
    y razone el tailoring (orden + resumen) antes de correr 'cv tailor'."""
    oferta = storage.obtener_por_url(_db_path(args.profile), args.url)
    if not oferta:
        console.print(f"[bold red]No se encontró ninguna oferta con url {args.url!r}[/bold red]")
        return 1
    console.print(f"[bold]Título:[/bold] {oferta.get('titulo', '')}")
    console.print(f"[bold]Empresa:[/bold] {oferta.get('empresa', '')}")
    console.print(f"[bold]Ubicación:[/bold] {oferta.get('ubicacion', '')}")
    console.print(f"[bold]Descripción:[/bold]\n{oferta.get('descripcion', '')}")
    return 0


def _parse_orden(valor: str) -> list:
    valor = valor.strip()
    if not valor:
        return []
    return [int(x) for x in valor.split(",")]


def cmd_cv_tailor(args) -> int:
    """Aplica un tailoring ya decidido por Claude Code (orden de work/skills +
    resumen nuevo, pasados como argumentos) y renderiza el PDF. No llama a
    ninguna API — el razonamiento ya está hecho antes de correr esto."""
    cv_path = Path("data") / f"{args.profile}-cv.json"
    if not cv_path.exists():
        console.print(
            f"[bold red]No hay CV guardado para '{args.profile}'. "
            f"Corre 'cli.py cv save <archivo.json> --profile {args.profile}' primero.[/bold red]"
        )
        return 1
    cv_base = json.loads(cv_path.read_text(encoding="utf-8"))

    oferta = storage.obtener_por_url(_db_path(args.profile), args.url)
    if not oferta:
        console.print(f"[bold red]No se encontró ninguna oferta con url {args.url!r}[/bold red]")
        return 1

    try:
        orden_work = _parse_orden(args.orden_work)
        orden_skills = _parse_orden(args.orden_skills)
    except ValueError as e:
        console.print(
            f"[bold red]--orden-work/--orden-skills debe ser una lista de índices "
            f"separados por coma: {e}[/bold red]"
        )
        return 1

    tailored = cv.aplicar_tailoring(cv_base, orden_work, orden_skills, args.summary)
    oferta_id = cv.id_oferta(args.url)
    tailored_dir = Path("data") / f"{args.profile}-tailored"
    tailored_dir.mkdir(parents=True, exist_ok=True)
    json_path = tailored_dir / f"{oferta_id}.json"
    json_path.write_text(json.dumps(tailored, ensure_ascii=False, indent=2), encoding="utf-8")

    pdf_path = tailored_dir / f"{oferta_id}.pdf"
    try:
        cv.renderizar_cv(json_path, pdf_path)
    except RuntimeError as e:
        console.print(f"[bold red]{e}[/bold red]")
        return 1

    console.print(f"[bold green]✓ Resume generado: {pdf_path}[/bold green]")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py")
    sub = parser.add_subparsers(dest="comando", required=True)

    p_list = sub.add_parser("list")
    p_list.add_argument("--profile", required=True)
    p_list.add_argument("--status", default=None, choices=sorted(storage.ESTADOS_VALIDOS))
    p_list.add_argument("--no-anim", action="store_true")
    p_list.set_defaults(func=cmd_list)

    p_mark = sub.add_parser("mark")
    p_mark.add_argument("--profile", required=True)
    p_mark.add_argument("url")
    p_mark.add_argument("estado", choices=sorted(storage.ESTADOS_VALIDOS))
    p_mark.add_argument("--no-anim", action="store_true")
    p_mark.set_defaults(func=cmd_mark)

    p_cv = sub.add_parser("cv")
    cv_sub = p_cv.add_subparsers(dest="cv_comando", required=True)

    p_cv_save = cv_sub.add_parser("save")
    p_cv_save.add_argument("archivo")
    p_cv_save.add_argument("--profile", required=True)
    p_cv_save.set_defaults(func=cmd_cv_save)

    p_cv_show = cv_sub.add_parser("show-offer")
    p_cv_show.add_argument("--profile", required=True)
    p_cv_show.add_argument("url")
    p_cv_show.set_defaults(func=cmd_cv_show_offer)

    p_cv_tailor = cv_sub.add_parser("tailor")
    p_cv_tailor.add_argument("--profile", required=True)
    p_cv_tailor.add_argument("url")
    p_cv_tailor.add_argument("--summary", required=True)
    p_cv_tailor.add_argument("--orden-work", default="", dest="orden_work")
    p_cv_tailor.add_argument("--orden-skills", default="", dest="orden_skills")
    p_cv_tailor.set_defaults(func=cmd_cv_tailor)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
