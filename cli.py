import argparse
import random
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.table import Table

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

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
