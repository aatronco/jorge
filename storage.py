import sqlite3
from pathlib import Path

ESTADOS_VALIDOS = {"nuevo", "aplicado", "duplicado", "descartado"}

_CAMPOS = ["titulo", "empresa", "ubicacion", "fecha_publicacion", "descripcion", "fuente"]


def init_db(path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ofertas (
            url TEXT PRIMARY KEY,
            titulo TEXT,
            empresa TEXT,
            ubicacion TEXT,
            fecha_publicacion TEXT,
            descripcion TEXT,
            fuente TEXT,
            estado TEXT NOT NULL DEFAULT 'nuevo',
            first_seen TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()
    conn.close()


def guardar(ofertas: list[dict], path) -> int:
    """Inserta solo ofertas nuevas por url. Nunca sobreescribe estado. Retorna cuántas nuevas."""
    init_db(path)
    conn = sqlite3.connect(path)
    nuevas = 0
    for o in ofertas:
        url = o.get("url", "")
        if not url:
            continue
        existe = conn.execute("SELECT 1 FROM ofertas WHERE url = ?", (url,)).fetchone()
        if existe:
            continue
        conn.execute(
            "INSERT INTO ofertas (url, titulo, empresa, ubicacion, fecha_publicacion, descripcion, fuente) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (url, *(o.get(campo, "") for campo in _CAMPOS)),
        )
        nuevas += 1
    conn.commit()
    conn.close()
    return nuevas


def listar(path, estado: str | None = None) -> list[dict]:
    init_db(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    if estado:
        rows = conn.execute(
            "SELECT * FROM ofertas WHERE estado = ? ORDER BY first_seen DESC", (estado,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM ofertas ORDER BY first_seen DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def obtener_por_url(path, url: str) -> dict | None:
    init_db(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM ofertas WHERE url = ?", (url,)).fetchone()
    conn.close()
    return dict(row) if row else None


def marcar(path, url: str, estado: str) -> bool:
    if estado not in ESTADOS_VALIDOS:
        raise ValueError(f"Estado inválido: {estado!r}. Válidos: {sorted(ESTADOS_VALIDOS)}")
    init_db(path)
    conn = sqlite3.connect(path)
    cur = conn.execute("UPDATE ofertas SET estado = ? WHERE url = ?", (estado, url))
    conn.commit()
    actualizado = cur.rowcount > 0
    conn.close()
    return actualizado
