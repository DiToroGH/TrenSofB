import json
import os
import sqlite3
import tempfile
import unittest
from datetime import date

from infra import repositories as repo
from infra.migrations import LINEA_SOFB_ID, LINEA_SOFB_NOMBRE, run_pending


class TestMigrations(unittest.TestCase):
    def setUp(self):
        self._prev_db = repo.DB_FILE
        self._prev_state = repo.STATE_FILE
        self.tmp = tempfile.TemporaryDirectory()
        repo.DB_FILE = os.path.join(self.tmp.name, "legacy.db")
        repo.STATE_FILE = os.path.join(self.tmp.name, "legacy.json")
        self._create_v1_db()
        self._create_v1_state()

    def tearDown(self):
        self.tmp.cleanup()
        repo.DB_FILE = self._prev_db
        repo.STATE_FILE = self._prev_state

    def _create_v1_db(self):
        conn = sqlite3.connect(repo.DB_FILE)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE conductores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL UNIQUE,
                    orden INTEGER NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE acompaniantes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL UNIQUE,
                    orden INTEGER NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE registro_dia (
                    fecha TEXT PRIMARY KEY,
                    conductor TEXT NOT NULL,
                    acompanante TEXT
                )
                """
            )
            cur.executemany(
                "INSERT INTO conductores (nombre, orden) VALUES (?, ?)",
                [("CondA", 0), ("CondB", 1)],
            )
            cur.executemany(
                "INSERT INTO acompaniantes (nombre, orden) VALUES (?, ?)",
                [("Acomp1", 0), ("Acomp2", 1)],
            )
            cur.execute(
                "INSERT INTO registro_dia (fecha, conductor, acompanante) VALUES (?, ?, ?)",
                ("2020-01-01", "CondA", "Acomp1"),
            )
            conn.commit()
        finally:
            conn.close()

    def _create_v1_state(self):
        estado = {
            "fecha": "2020-01-02",
            "acompaniantes_orden": ["Acomp1", "Acomp2"],
            "no_disponibles_hoy": [],
            "asignaciones_hoy": [["CondA", "Acomp1"]],
        }
        with open(repo.STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(estado, f)

    def test_migrate_v1_to_v2_preserves_data(self):
        run_pending(repo.DB_FILE, repo.STATE_FILE)

        lineas = repo.listar_lineas()
        self.assertEqual(len(lineas), 1)
        self.assertEqual(lineas[0], (LINEA_SOFB_ID, LINEA_SOFB_NOMBRE, True))

        conductores = repo.cargar_conductores(LINEA_SOFB_ID)
        self.assertEqual(conductores, ["CondA", "CondB"])

        acomps = repo.cargar_acompaniantes(LINEA_SOFB_ID)
        self.assertEqual(acomps, ["Acomp1", "Acomp2"])

        registros = repo.list_registro_dias_entre("2020-01-01", "2020-01-01", LINEA_SOFB_ID)
        self.assertEqual(len(registros), 1)
        self.assertEqual(registros[0], ("2020-01-01", "CondA", "Acomp1", None))

        estado = repo.cargar_estado(LINEA_SOFB_ID)
        self.assertEqual(estado["fecha"], "2020-01-02")
        self.assertEqual(estado["acompaniantes_orden"], ["Acomp1", "Acomp2"])
        self.assertEqual(estado["asignaciones_hoy"], [["CondA", "Acomp1"]])

        with open(repo.STATE_FILE, "r", encoding="utf-8") as f:
            root = json.load(f)
        self.assertEqual(root["schema_version"], 2)
        self.assertIn("1", root["lineas"])

    def test_migration_idempotent(self):
        run_pending(repo.DB_FILE, repo.STATE_FILE)
        run_pending(repo.DB_FILE, repo.STATE_FILE)
        self.assertEqual(repo.cargar_conductores(LINEA_SOFB_ID), ["CondA", "CondB"])

    def test_fresh_init_creates_sofb_line(self):
        repo.DB_FILE = os.path.join(self.tmp.name, "fresh.db")
        repo.STATE_FILE = os.path.join(self.tmp.name, "fresh.json")
        repo.inicializar_db()
        lineas = repo.listar_lineas()
        self.assertTrue(any(n == LINEA_SOFB_NOMBRE for _id, n, _v in lineas))
        self.assertGreater(len(repo.cargar_conductores()), 0)
