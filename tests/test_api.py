import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from api.main import app
from infra import repositories as repo


class TestApiAislada(unittest.TestCase):
    def setUp(self):
        self._prev_db = repo.DB_FILE
        self._prev_state = repo.STATE_FILE
        self.tmp = tempfile.TemporaryDirectory()
        repo.DB_FILE = os.path.join(self.tmp.name, "test_tren.db")
        repo.STATE_FILE = os.path.join(self.tmp.name, "test_estado.json")
        repo.inicializar_db()
        self.client = TestClient(app)

    def tearDown(self):
        self.tmp.cleanup()
        repo.DB_FILE = self._prev_db
        repo.STATE_FILE = self._prev_state

    def test_health(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")

    def test_index_y_static(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"SofB Train", r.content)
        r2 = self.client.get("/static/app.js")
        self.assertEqual(r2.status_code, 200)
        r3 = self.client.get("/static/gestion_personas.js")
        self.assertEqual(r3.status_code, 200)

    def test_generar_y_cerrar(self):
        r = self.client.get("/estado/hoy")
        self.assertEqual(r.status_code, 200)
        self.assertGreater(len(r.json()["conductores"]), 0)

        r = self.client.post("/asignacion/generar", json={})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertGreater(len(body["asignaciones"]), 0)
        self.assertIn("mensaje_turno", body)
        self.assertIsInstance(body["mensaje_turno"], (str, type(None)))
        self.assertTrue(body["mensaje_turno"])

        r = self.client.post("/dia/cerrar")
        self.assertEqual(r.status_code, 200)
        self.assertIn("mensaje", r.json())

        r = self.client.get("/estado/hoy")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["asignaciones"], [])

    def test_generar_con_disponibles_vacio_sin_acompaniante(self):
        r = self.client.post("/asignacion/generar", json={"disponibles": []})
        self.assertEqual(r.status_code, 200)
        body = r.json()
        for item in body["asignaciones"]:
            self.assertEqual(item["acompanante"], "SIN ACOMPAÑANTE")

    def test_personas_conductores_list(self):
        r = self.client.get("/personas/conductores")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertGreaterEqual(len(data), 1)
        self.assertIn("id", data[0])
        self.assertIn("nombre", data[0])

    def test_personas_acompanientes_alta_y_baja(self):
        r = self.client.post(
            "/personas/acompaniantes",
            json={"nombre": "Test Web SofB XY"},
        )
        self.assertEqual(r.status_code, 201)
        pid = r.json()["id"]
        r2 = self.client.delete(f"/personas/acompaniantes/{pid}")
        self.assertEqual(r2.status_code, 204)


if __name__ == "__main__":
    unittest.main()
