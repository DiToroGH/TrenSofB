"""Migraciones idempotentes de SQLite y estado JSON."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import date

log = logging.getLogger(__name__)

SCHEMA_VERSION = 4
LINEA_SOFB_ID = 1
LINEA_SOFB_NOMBRE = "SofB"

_STATE_KEYS = (
    "fecha",
    "acompaniantes_orden",
    "no_disponibles_hoy",
    "asignaciones_hoy",
    "disponibles_hoy",
    "mensaje_turno",
    "segundo_acompanante_hoy",
)


def _table_has_column(cur: sqlite3.Cursor, table: str, column: str) -> bool:
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def _table_exists(cur: sqlite3.Cursor, table: str) -> bool:
    cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    return cur.fetchone() is not None


def _get_schema_version(cur: sqlite3.Cursor) -> int:
    if not _table_exists(cur, "schema_meta"):
        return 0
    cur.execute("SELECT version FROM schema_meta LIMIT 1")
    row = cur.fetchone()
    return int(row[0]) if row else 0


def _set_schema_version(cur: sqlite3.Cursor, version: int) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_meta (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            version INTEGER NOT NULL
        )
        """
    )
    cur.execute(
        """
        INSERT INTO schema_meta (id, version) VALUES (1, ?)
        ON CONFLICT(id) DO UPDATE SET version = excluded.version
        """,
        (version,),
    )


def _ensure_lineas_table(cur: sqlite3.Cursor) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS lineas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            creado_en TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    cur.execute("SELECT id FROM lineas WHERE id = ?", (LINEA_SOFB_ID,))
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO lineas (id, nombre) VALUES (?, ?)",
            (LINEA_SOFB_ID, LINEA_SOFB_NOMBRE),
        )


def _migrate_personas_table(cur: sqlite3.Cursor, tabla: str) -> None:
    if _table_has_column(cur, tabla, "linea_id"):
        return
    cur.execute(
        f"""
        CREATE TABLE {tabla}_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            linea_id INTEGER NOT NULL DEFAULT 1,
            nombre TEXT NOT NULL,
            orden INTEGER NOT NULL,
            UNIQUE (linea_id, nombre),
            FOREIGN KEY (linea_id) REFERENCES lineas(id)
        )
        """
    )
    cur.execute(
        f"""
        INSERT INTO {tabla}_new (id, linea_id, nombre, orden)
        SELECT id, ?, nombre, orden FROM {tabla}
        """,
        (LINEA_SOFB_ID,),
    )
    cur.execute(f"DROP TABLE {tabla}")
    cur.execute(f"ALTER TABLE {tabla}_new RENAME TO {tabla}")


def _migrate_registro_dia(cur: sqlite3.Cursor) -> None:
    if not _table_exists(cur, "registro_dia"):
        cur.execute(
            """
            CREATE TABLE registro_dia (
                linea_id INTEGER NOT NULL DEFAULT 1,
                fecha TEXT NOT NULL,
                conductor TEXT NOT NULL,
                acompanante TEXT,
                segundo_acompanante TEXT,
                PRIMARY KEY (linea_id, fecha),
                FOREIGN KEY (linea_id) REFERENCES lineas(id)
            )
            """
        )
        return
    if _table_has_column(cur, "registro_dia", "linea_id"):
        return
    cur.execute(
        """
        CREATE TABLE registro_dia_new (
            linea_id INTEGER NOT NULL DEFAULT 1,
            fecha TEXT NOT NULL,
            conductor TEXT NOT NULL,
            acompanante TEXT,
            PRIMARY KEY (linea_id, fecha),
            FOREIGN KEY (linea_id) REFERENCES lineas(id)
        )
        """
    )
    cur.execute(
        """
        INSERT INTO registro_dia_new (linea_id, fecha, conductor, acompanante)
        SELECT ?, fecha, conductor, acompanante FROM registro_dia
        """,
        (LINEA_SOFB_ID,),
    )
    cur.execute("DROP TABLE registro_dia")
    cur.execute("ALTER TABLE registro_dia_new RENAME TO registro_dia")


def _migrate_db_v1_to_v2(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    _ensure_lineas_table(cur)
    if _table_exists(cur, "conductores"):
        _migrate_personas_table(cur, "conductores")
    if _table_exists(cur, "acompaniantes"):
        _migrate_personas_table(cur, "acompaniantes")
    _migrate_registro_dia(cur)
    _set_schema_version(cur, 2)
    conn.commit()
    log.info("Migración SQLite v1 → v2 completada (línea por defecto: %s).", LINEA_SOFB_NOMBRE)


def _migrate_registro_segundo_acompanante(cur: sqlite3.Cursor) -> None:
    if not _table_exists(cur, "registro_dia"):
        return
    if _table_has_column(cur, "registro_dia", "segundo_acompanante"):
        return
    cur.execute("ALTER TABLE registro_dia ADD COLUMN segundo_acompanante TEXT")


def _migrate_db_v2_to_v3(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    _migrate_registro_segundo_acompanante(cur)
    _set_schema_version(cur, 3)
    conn.commit()
    log.info("Migración SQLite v2 → v3 completada (segundo acompañante en registro).")


def _migrate_lineas_visible(cur: sqlite3.Cursor) -> None:
    if not _table_exists(cur, "lineas"):
        return
    if _table_has_column(cur, "lineas", "visible"):
        return
    cur.execute("ALTER TABLE lineas ADD COLUMN visible INTEGER NOT NULL DEFAULT 1")


def _migrate_db_v3_to_v4(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    _migrate_lineas_visible(cur)
    _set_schema_version(cur, 4)
    conn.commit()
    log.info("Migración SQLite v3 → v4 completada (visibilidad de líneas).")


def migrate_state_file(state_path: str) -> None:
    import os

    if not os.path.exists(state_path):
        return
    with open(state_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if data.get("schema_version") == 2:
        return
    linea_state: dict = {}
    for key in _STATE_KEYS:
        if key in data:
            linea_state[key] = data[key]
    if "fecha" not in linea_state:
        linea_state["fecha"] = str(date.today())
    if "acompaniantes_orden" not in linea_state:
        linea_state["acompaniantes_orden"] = []
    if "no_disponibles_hoy" not in linea_state:
        linea_state["no_disponibles_hoy"] = []
    new_data = {
        "schema_version": 2,
        "lineas": {str(LINEA_SOFB_ID): linea_state},
    }
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)
    log.info("Estado JSON migrado a v2 (línea %s).", LINEA_SOFB_ID)


def run_pending(db_path: str, state_path: str) -> None:
    """Ejecuta migraciones pendientes de DB y JSON."""
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        version = _get_schema_version(cur)
        if version < 2:
            _migrate_db_v1_to_v2(conn)
            version = _get_schema_version(conn.cursor())
        if version < 3:
            _migrate_db_v2_to_v3(conn)
            version = _get_schema_version(conn.cursor())
        if version < 4:
            _migrate_db_v3_to_v4(conn)
    finally:
        conn.close()
    migrate_state_file(state_path)
