import json
import os
import sqlite3
from datetime import date


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


def listar_personas(tabla):
    conn = sqlite3.connect(DB_FILE)
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT id, nombre FROM {tabla} ORDER BY orden, id")
        return cur.fetchall()
    finally:
        conn.close()


def cargar_conductores():
    return [row[1] for row in listar_personas("conductores")]


def cargar_acompaniantes():
    return [row[1] for row in listar_personas("acompaniantes")]


def insertar_persona(tabla, nombre):
    conn = sqlite3.connect(DB_FILE)
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT COALESCE(MAX(orden), -1) + 1 FROM {tabla}")
        nuevo_orden = cur.fetchone()[0]
        cur.execute(
            f"INSERT INTO {tabla} (nombre, orden) VALUES (?, ?)",
            (nombre, nuevo_orden),
        )
        conn.commit()
    finally:
        conn.close()


def editar_persona(tabla, persona_id, nuevo_nombre):
    conn = sqlite3.connect(DB_FILE)
    try:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE {tabla} SET nombre = ? WHERE id = ?",
            (nuevo_nombre, persona_id),
        )
        conn.commit()
    finally:
        conn.close()


def borrar_persona(tabla, persona_id):
    conn = sqlite3.connect(DB_FILE)
    try:
        cur = conn.cursor()
        cur.execute(f"DELETE FROM {tabla} WHERE id = ?", (persona_id,))
        conn.commit()
    finally:
        conn.close()


def guardar_orden_personas(tabla, items):
    conn = sqlite3.connect(DB_FILE)
    try:
        cur = conn.cursor()
        for orden, (persona_id, _nombre) in enumerate(items):
            cur.execute(
                f"UPDATE {tabla} SET orden = ? WHERE id = ?",
                (orden, persona_id),
            )
        conn.commit()
    finally:
        conn.close()


def mover_persona_al_final(tabla, nombre):
    if not nombre:
        return
    items = listar_personas(tabla)
    idx = next((i for i, (_pid, n) in enumerate(items) if n == nombre), None)
    if idx is None:
        return
    movido = items.pop(idx)
    items.append(movido)
    guardar_orden_personas(tabla, items)


def cargar_estado():
    acompaniantes_db = cargar_acompaniantes()
    if not os.path.exists(STATE_FILE):
        return {
            "fecha": str(date.today()),
            "acompaniantes_orden": acompaniantes_db,
            "no_disponibles_hoy": [],
        }
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        estado = json.load(f)
    if "acompaniantes_orden" not in estado or not estado["acompaniantes_orden"]:
        estado["acompaniantes_orden"] = acompaniantes_db
    else:
        en_estado = estado["acompaniantes_orden"]
        faltantes = [a for a in acompaniantes_db if a not in en_estado]
        estado["acompaniantes_orden"] = [
            a for a in en_estado if a in acompaniantes_db
        ] + faltantes
    return estado


def guardar_estado(estado):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)
