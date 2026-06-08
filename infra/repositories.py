import json
import os
import sqlite3
from datetime import date

from infra.migrations import LINEA_SOFB_ID, run_pending


def _ensure_parent(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def _resolve_data_paths() -> tuple[str, str]:
    """
    Rutas de SQLite y JSON de estado.

    - TREN_DATA_DIR: directorio (por defecto el cwd). Se crea si no existe.
    - TREN_DB_PATH / TREN_STATE_PATH: rutas absolutas o relativas opcionales
      (si no se definen, van dentro de TREN_DATA_DIR).
    """
    data_dir = os.environ.get("TREN_DATA_DIR", ".").strip() or "."
    data_dir = os.path.abspath(data_dir)
    os.makedirs(data_dir, exist_ok=True)

    db = os.environ.get("TREN_DB_PATH")
    if db:
        db = os.path.abspath(db)
    else:
        db = os.path.join(data_dir, "datos_tren.db")

    state = os.environ.get("TREN_STATE_PATH")
    if state:
        state = os.path.abspath(state)
    else:
        state = os.path.join(data_dir, "estado_tren.json")

    _ensure_parent(db)
    _ensure_parent(state)
    return db, state


DB_FILE, STATE_FILE = _resolve_data_paths()
CONDUCTORES_SEED = [
    "Conductor 1", "Conductor 2", "Conductor 3", "Conductor 4"
]
ACOMPANIANTES_SEED = [
    "Acompañante A", "Acompañante B", "Acompañante C", "Acompañante D"
]

_STATE_KEYS = (
    "fecha",
    "acompaniantes_orden",
    "no_disponibles_hoy",
    "asignaciones_hoy",
    "disponibles_hoy",
    "mensaje_turno",
    "segundo_acompanante_hoy",
    "conductores_fijos_semana",
)


def inicializar_db():
    conn = sqlite3.connect(DB_FILE)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS conductores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                orden INTEGER NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS acompaniantes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                orden INTEGER NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS registro_dia (
                fecha TEXT PRIMARY KEY,
                conductor TEXT NOT NULL,
                acompanante TEXT
            )
            """
        )
        cur.execute("SELECT COUNT(*) FROM conductores")
        if cur.fetchone()[0] == 0:
            cur.executemany(
                "INSERT INTO conductores (nombre, orden) VALUES (?, ?)",
                [(nombre, idx) for idx, nombre in enumerate(CONDUCTORES_SEED)]
            )
        cur.execute("SELECT COUNT(*) FROM acompaniantes")
        if cur.fetchone()[0] == 0:
            cur.executemany(
                "INSERT INTO acompaniantes (nombre, orden) VALUES (?, ?)",
                [(nombre, idx) for idx, nombre in enumerate(ACOMPANIANTES_SEED)]
            )
        conn.commit()
    finally:
        conn.close()
    run_pending(DB_FILE, STATE_FILE)


def _estado_default_linea(acompaniantes_db: list[str]) -> dict:
    return {
        "fecha": str(date.today()),
        "acompaniantes_orden": list(acompaniantes_db),
        "no_disponibles_hoy": [],
    }


def _load_state_root() -> dict:
    if not os.path.exists(STATE_FILE):
        return {"schema_version": 2, "lineas": {}}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if data.get("schema_version") != 2:
        run_pending(DB_FILE, STATE_FILE)
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    return data


def _save_state_root(root: dict) -> None:
    root["schema_version"] = 2
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(root, f, ensure_ascii=False, indent=2)


def listar_personas(tabla: str, linea_id: int = LINEA_SOFB_ID):
    conn = sqlite3.connect(DB_FILE)
    try:
        cur = conn.cursor()
        cur.execute(
            f"SELECT id, nombre FROM {tabla} WHERE linea_id = ? ORDER BY orden, id",
            (linea_id,),
        )
        return cur.fetchall()
    finally:
        conn.close()


def cargar_conductores(linea_id: int = LINEA_SOFB_ID):
    return [row[1] for row in listar_personas("conductores", linea_id)]


def cargar_acompaniantes(linea_id: int = LINEA_SOFB_ID):
    return [row[1] for row in listar_personas("acompaniantes", linea_id)]


def insertar_persona(tabla: str, nombre: str, linea_id: int = LINEA_SOFB_ID):
    conn = sqlite3.connect(DB_FILE)
    try:
        cur = conn.cursor()
        cur.execute(
            f"SELECT COALESCE(MAX(orden), -1) + 1 FROM {tabla} WHERE linea_id = ?",
            (linea_id,),
        )
        nuevo_orden = cur.fetchone()[0]
        cur.execute(
            f"INSERT INTO {tabla} (linea_id, nombre, orden) VALUES (?, ?, ?)",
            (linea_id, nombre, nuevo_orden),
        )
        conn.commit()
    finally:
        conn.close()


def editar_persona(
    tabla: str, persona_id: int, nuevo_nombre: str, linea_id: int = LINEA_SOFB_ID
):
    conn = sqlite3.connect(DB_FILE)
    try:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE {tabla} SET nombre = ? WHERE id = ? AND linea_id = ?",
            (nuevo_nombre, persona_id, linea_id),
        )
        conn.commit()
    finally:
        conn.close()


def borrar_persona(tabla: str, persona_id: int, linea_id: int = LINEA_SOFB_ID):
    conn = sqlite3.connect(DB_FILE)
    try:
        cur = conn.cursor()
        cur.execute(
            f"DELETE FROM {tabla} WHERE id = ? AND linea_id = ?",
            (persona_id, linea_id),
        )
        conn.commit()
    finally:
        conn.close()


def guardar_orden_personas(
    tabla: str, items, linea_id: int = LINEA_SOFB_ID
):
    conn = sqlite3.connect(DB_FILE)
    try:
        cur = conn.cursor()
        for orden, (persona_id, _nombre) in enumerate(items):
            cur.execute(
                f"UPDATE {tabla} SET orden = ? WHERE id = ? AND linea_id = ?",
                (orden, persona_id, linea_id),
            )
        conn.commit()
    finally:
        conn.close()


def mover_persona_al_final(tabla: str, nombre: str, linea_id: int = LINEA_SOFB_ID):
    if not nombre:
        return
    items = listar_personas(tabla, linea_id)
    idx = next((i for i, (_pid, n) in enumerate(items) if n == nombre), None)
    if idx is None:
        return
    movido = items.pop(idx)
    items.append(movido)
    guardar_orden_personas(tabla, items, linea_id)


def cargar_estado(linea_id: int = LINEA_SOFB_ID):
    acompaniantes_db = cargar_acompaniantes(linea_id)
    root = _load_state_root()
    key = str(linea_id)
    lineas = root.setdefault("lineas", {})
    if key not in lineas:
        estado = _estado_default_linea(acompaniantes_db)
    else:
        estado = dict(lineas[key])
    if "acompaniantes_orden" not in estado or not estado["acompaniantes_orden"]:
        estado["acompaniantes_orden"] = acompaniantes_db
    else:
        en_estado = estado["acompaniantes_orden"]
        faltantes = [a for a in acompaniantes_db if a not in en_estado]
        estado["acompaniantes_orden"] = [
            a for a in en_estado if a in acompaniantes_db
        ] + faltantes
    return estado


def guardar_estado(estado: dict, linea_id: int = LINEA_SOFB_ID):
    root = _load_state_root()
    linea_state = {k: estado[k] for k in _STATE_KEYS if k in estado}
    for k, v in estado.items():
        if k not in linea_state and k not in ("schema_version", "lineas"):
            linea_state[k] = v
    root.setdefault("lineas", {})[str(linea_id)] = linea_state
    _save_state_root(root)


def inicializar_estado_linea(linea_id: int) -> None:
    root = _load_state_root()
    key = str(linea_id)
    if key in root.get("lineas", {}):
        return
    acomps = cargar_acompaniantes(linea_id)
    root.setdefault("lineas", {})[key] = _estado_default_linea(acomps)
    _save_state_root(root)


def upsert_registro_dia(
    fecha: str,
    conductor: str,
    acompanante: str | None,
    linea_id: int = LINEA_SOFB_ID,
) -> None:
    conn = sqlite3.connect(DB_FILE)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO registro_dia (linea_id, fecha, conductor, acompanante)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(linea_id, fecha) DO UPDATE SET
                conductor = excluded.conductor,
                acompanante = excluded.acompanante
            """,
            (linea_id, fecha, conductor, acompanante),
        )
        conn.commit()
    finally:
        conn.close()


def purgar_registro_antes_de(
    fecha_limite: str, linea_id: int = LINEA_SOFB_ID
) -> None:
    conn = sqlite3.connect(DB_FILE)
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM registro_dia WHERE linea_id = ? AND fecha < ?",
            (linea_id, fecha_limite),
        )
        conn.commit()
    finally:
        conn.close()


def list_registro_dias_entre(
    desde: str, hasta: str, linea_id: int = LINEA_SOFB_ID
) -> list[tuple[str, str, str | None]]:
    conn = sqlite3.connect(DB_FILE)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT fecha, conductor, acompanante
            FROM registro_dia
            WHERE linea_id = ? AND fecha >= ? AND fecha <= ?
            ORDER BY fecha
            """,
            (linea_id, desde, hasta),
        )
        rows = cur.fetchall()
        out: list[tuple[str, str, str | None]] = []
        for fecha, conductor, acomp in rows:
            out.append((fecha, conductor, acomp if acomp is not None else None))
        return out
    finally:
        conn.close()


def listar_lineas() -> list[tuple[int, str]]:
    conn = sqlite3.connect(DB_FILE)
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, nombre FROM lineas ORDER BY id")
        return [(int(row[0]), row[1]) for row in cur.fetchall()]
    finally:
        conn.close()


def obtener_linea(linea_id: int) -> tuple[int, str] | None:
    conn = sqlite3.connect(DB_FILE)
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, nombre FROM lineas WHERE id = ?", (linea_id,))
        row = cur.fetchone()
        if row is None:
            return None
        return int(row[0]), row[1]
    finally:
        conn.close()


def linea_existe(linea_id: int) -> bool:
    return obtener_linea(linea_id) is not None


def crear_linea(nombre: str) -> int:
    conn = sqlite3.connect(DB_FILE)
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO lineas (nombre) VALUES (?)", (nombre.strip(),))
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def renombrar_linea(linea_id: int, nombre: str) -> None:
    conn = sqlite3.connect(DB_FILE)
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE lineas SET nombre = ? WHERE id = ?",
            (nombre.strip(), linea_id),
        )
        conn.commit()
    finally:
        conn.close()


def linea_tiene_datos(linea_id: int) -> bool:
    conn = sqlite3.connect(DB_FILE)
    try:
        cur = conn.cursor()
        for tabla in ("conductores", "acompaniantes", "registro_dia"):
            cur.execute(
                f"SELECT 1 FROM {tabla} WHERE linea_id = ? LIMIT 1",
                (linea_id,),
            )
            if cur.fetchone():
                return True
        return False
    finally:
        conn.close()


def borrar_linea(linea_id: int) -> None:
    if linea_id == LINEA_SOFB_ID:
        raise ValueError("No se puede eliminar la línea SofB.")
    if linea_tiene_datos(linea_id):
        raise ValueError("La línea tiene datos; no se puede eliminar.")
    conn = sqlite3.connect(DB_FILE)
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM lineas WHERE id = ?", (linea_id,))
        conn.commit()
    finally:
        conn.close()
    root = _load_state_root()
    lineas = root.get("lineas", {})
    lineas.pop(str(linea_id), None)
    _save_state_root(root)
