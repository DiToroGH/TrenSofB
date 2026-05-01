import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from api.main import app
from infra import repositories as repo


def _admin_auth_headers(client: TestClient) -> dict[str, str]:
    r = client.post("/login", json={"username": "admin", "password": "Germany10"})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


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
        h = _admin_auth_headers(self.client)
        r = self.client.get("/estado/hoy", headers=h)
        self.assertEqual(r.status_code, 200)
        self.assertGreater(len(r.json()["conductores"]), 0)

        r = self.client.post("/asignacion/generar", json={}, headers=h)
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertGreater(len(body["asignaciones"]), 0)
        self.assertIn("mensaje_turno", body)
        self.assertIsInstance(body["mensaje_turno"], (str, type(None)))
        self.assertTrue(body["mensaje_turno"])

        r = self.client.post("/dia/cerrar", headers=h)
        self.assertEqual(r.status_code, 200)
        self.assertIn("mensaje", r.json())

        r = self.client.get("/estado/hoy", headers=h)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["asignaciones"], [])

    def test_generar_con_disponibles_vacio_sin_acompaniante(self):
        h = _admin_auth_headers(self.client)
        r = self.client.post("/asignacion/generar", json={"disponibles": []}, headers=h)
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
        h = _admin_auth_headers(self.client)
        r = self.client.post(
            "/personas/acompaniantes",
            json={"nombre": "Test Web SofB XY"},
            headers=h,
        )
        self.assertEqual(r.status_code, 201)
        pid = r.json()["id"]
        r2 = self.client.delete(f"/personas/acompaniantes/{pid}", headers=h)
        self.assertEqual(r2.status_code, 204)

    def test_estado_hoy_conductores_items_alineados(self):
        h = _admin_auth_headers(self.client)
        r = self.client.get("/estado/hoy", headers=h)
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("conductores_items", body)
        items = body["conductores_items"]
        nombres = body["conductores"]
        self.assertEqual(len(items), len(nombres))
        for i, row in enumerate(items):
            self.assertIn("id", row)
            self.assertIn("nombre", row)
            self.assertEqual(row["nombre"], nombres[i])

    def test_mover_conductor_al_final_manual(self):
        h = _admin_auth_headers(self.client)
        r = self.client.get("/estado/hoy", headers=h)
        items = r.json()["conductores_items"]
        self.assertGreaterEqual(len(items), 2)
        primero_id = items[0]["id"]
        r2 = self.client.post(
            "/personas/conductores/mover-extremo",
            json={"persona_id": primero_id, "al_inicio": False},
            headers=h,
        )
        self.assertEqual(r2.status_code, 204)
        r3 = self.client.get("/estado/hoy", headers=h)
        nombres_despues = r3.json()["conductores"]
        self.assertEqual(nombres_despues[-1], items[0]["nombre"])


if __name__ == "__main__":
    unittest.main()
