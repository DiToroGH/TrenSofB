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


def _user_auth_headers(client: TestClient) -> dict[str, str]:
    r = client.post("/login", json={"username": "user", "password": "user123"})
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

    def test_estado_hoy_acompaniantes_items_alineados_con_orden(self):
        h = _admin_auth_headers(self.client)
        r = self.client.get("/estado/hoy", headers=h)
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("acompaniantes_items", body)
        orden = body["acompaniantes_orden"]
        items = body["acompaniantes_items"]
        self.assertEqual(len(items), len(orden))
        for i, row in enumerate(items):
            self.assertIn("id", row)
            self.assertIn("nombre", row)
            self.assertEqual(row["nombre"], orden[i])

    def test_mover_acompaniante_al_final_manual(self):
        h = _admin_auth_headers(self.client)
        r = self.client.get("/estado/hoy", headers=h)
        items = r.json()["acompaniantes_items"]
        orden_antes = r.json()["acompaniantes_orden"]
        self.assertGreaterEqual(len(items), 2)
        primero_id = items[0]["id"]
        r2 = self.client.post(
            "/personas/acompaniantes/mover-extremo",
            json={"persona_id": primero_id, "al_inicio": False},
            headers=h,
        )
        self.assertEqual(r2.status_code, 204)
        r3 = self.client.get("/estado/hoy", headers=h)
        orden_despues = r3.json()["acompaniantes_orden"]
        self.assertEqual(orden_despues[-1], orden_antes[0])
        # El JSON debe reflejar el movimiento (antes solo cambiaba SQLite).
        self.assertNotEqual(orden_despues, orden_antes)

    def test_cerrar_guarda_registro_dia(self):
        h = _admin_auth_headers(self.client)
        r = self.client.get("/estado/hoy", headers=h)
        self.assertEqual(r.status_code, 200)
        fecha_estado = r.json()["fecha"]
        self.client.post("/asignacion/generar", json={}, headers=h)
        r_c = self.client.post("/dia/cerrar", headers=h)
        self.assertEqual(r_c.status_code, 200)
        r2 = self.client.get(
            "/registro/dias",
            params={"desde": fecha_estado, "hasta": fecha_estado},
            headers=h,
        )
        self.assertEqual(r2.status_code, 200)
        rows = r2.json()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["fecha"], fecha_estado)
        self.assertIn("conductor", rows[0])
        self.assertIn("acompanante", rows[0])

    def test_guardar_y_regenerar_mensaje_turno(self):
        h = _admin_auth_headers(self.client)
        custom = "Mensaje de prueba personalizado."
        r = self.client.put(
            "/estado/mensaje-turno",
            json={"mensaje": custom},
            headers=h,
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["mensaje_turno"], custom)

        r2 = self.client.get("/estado/hoy", headers=h)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["mensaje_turno"], custom)

        r3 = self.client.post("/estado/mensaje-turno/regenerar", headers=h)
        self.assertEqual(r3.status_code, 200)
        self.assertNotEqual(r3.json()["mensaje_turno"], custom)

    def test_segundo_acompaniante_y_cierre(self):
        h = _admin_auth_headers(self.client)
        r = self.client.get("/estado/hoy", headers=h)
        orden = r.json()["acompaniantes_orden"]
        fecha_estado = r.json()["fecha"]
        self.assertGreaterEqual(len(orden), 2)
        vip = orden[0]
        segundo = orden[1]
        r2 = self.client.put(
            "/estado/segundo-acompanante",
            json={"nombre": segundo},
            headers=h,
        )
        self.assertEqual(r2.status_code, 200)
        r3 = self.client.get("/estado/hoy", headers=h)
        self.assertEqual(r3.json()["segundo_acompanante"], segundo)
        r4 = self.client.put(
            "/estado/segundo-acompanante",
            json={"nombre": vip},
            headers=h,
        )
        self.assertEqual(r4.status_code, 400)
        self.client.post("/asignacion/generar", json={}, headers=h)
        r_c = self.client.post("/dia/cerrar", headers=h)
        self.assertEqual(r_c.status_code, 200)
        r_reg = self.client.get(
            "/registro/dias",
            params={"desde": fecha_estado, "hasta": fecha_estado},
            headers=h,
        )
        self.assertEqual(r_reg.status_code, 200)
        rows = r_reg.json()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["segundo_acompanante"], segundo)

    def test_put_registro_dia_pasado_sin_vip(self):
        h = _admin_auth_headers(self.client)
        r = self.client.get("/estado/hoy", headers=h)
        cond = r.json()["conductores"][0]
        from datetime import date, timedelta

        pasado = (date.today() - timedelta(days=3)).isoformat()
        r2 = self.client.put(
            f"/registro/dia/{pasado}",
            json={"conductor": cond, "acompanante": None},
            headers=h,
        )
        self.assertEqual(r2.status_code, 200, r2.text)
        body = r2.json()
        self.assertEqual(body["fecha"], pasado)
        self.assertEqual(body["conductor"], cond)
        self.assertIsNone(body["acompanante"])

    def test_put_registro_dia_pasado_acompaniante_como_conductor(self):
        h = _admin_auth_headers(self.client)
        r = self.client.get("/estado/hoy", headers=h)
        acomp = r.json()["acompaniantes_orden"][0]
        from datetime import date, timedelta

        pasado = (date.today() - timedelta(days=5)).isoformat()
        r2 = self.client.put(
            f"/registro/dia/{pasado}",
            json={"conductor": acomp, "acompanante": None},
            headers=h,
        )
        self.assertEqual(r2.status_code, 200, r2.text)
        self.assertEqual(r2.json()["conductor"], acomp)

    def test_put_registro_dia_hoy_confirmado(self):
        from datetime import date

        h = _admin_auth_headers(self.client)
        r = self.client.get("/estado/hoy", headers=h)
        hoy = r.json()["fecha"]
        cond = r.json()["conductores"][0]

        r_fail = self.client.put(
            f"/registro/dia/{hoy}",
            json={"conductor": cond, "acompanante": None},
            headers=h,
        )
        self.assertEqual(r_fail.status_code, 400)

        self.client.post("/asignacion/generar", json={}, headers=h)
        self.client.post("/dia/cerrar", headers=h)

        r_ok = self.client.put(
            f"/registro/dia/{hoy}",
            json={"conductor": cond, "acompanante": None},
            headers=h,
        )
        self.assertEqual(r_ok.status_code, 200, r_ok.text)
        self.assertEqual(r_ok.json()["fecha"], hoy)

    def test_linea_visibilidad_usuario(self):
        ha = _admin_auth_headers(self.client)
        hu = _user_auth_headers(self.client)

        r = self.client.post("/lineas", json={"nombre": "Linea Oculta"}, headers=ha)
        self.assertEqual(r.status_code, 201, r.text)
        linea_id = r.json()["id"]
        self.assertFalse(r.json()["visible"])

        r_user = self.client.get("/lineas", headers=hu)
        self.assertEqual(r_user.status_code, 200)
        ids_user = [x["id"] for x in r_user.json()]
        self.assertNotIn(linea_id, ids_user)
        self.assertIn(1, ids_user)

        r_vis = self.client.patch(
            f"/lineas/{linea_id}/visible",
            json={"visible": True},
            headers=ha,
        )
        self.assertEqual(r_vis.status_code, 200)
        self.assertTrue(r_vis.json()["visible"])

        r_user2 = self.client.get("/lineas", headers=hu)
        ids_user2 = [x["id"] for x in r_user2.json()]
        self.assertIn(linea_id, ids_user2)

        r_hide = self.client.patch(
            "/lineas/1/visible",
            json={"visible": False},
            headers=ha,
        )
        self.assertEqual(r_hide.status_code, 400)

    def test_conductores_fijos_semana(self):
        h = _admin_auth_headers(self.client)
        r = self.client.get("/estado/hoy", headers=h)
        cond = r.json()["conductores"][0]
        r2 = self.client.put(
            "/estado/conductores-fijos-semana",
            json={"dia_semana": 6, "conductor": cond},
            headers=h,
        )
        self.assertEqual(r2.status_code, 200, r2.text)
        self.assertEqual(r2.json()["conductores_fijos_semana"]["6"], cond)
        r3 = self.client.put(
            "/estado/conductores-fijos-semana",
            json={"dia_semana": 6, "conductor": None},
            headers=h,
        )
        self.assertEqual(r3.status_code, 200)
        self.assertNotIn("6", r3.json()["conductores_fijos_semana"])

    def test_estado_hoy_incluye_linea(self):
        h = _admin_auth_headers(self.client)
        r = self.client.get("/estado/hoy", headers=h)
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["linea_id"], 1)
        self.assertEqual(body["linea_nombre"], "SofB")

    def test_lineas_crud_y_aislamiento(self):
        h = _admin_auth_headers(self.client)
        r = self.client.get("/lineas", headers=h)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(any(x["nombre"] == "SofB" for x in r.json()))

        r2 = self.client.post(
            "/lineas",
            json={"nombre": "Linea Test B"},
            headers=h,
        )
        self.assertEqual(r2.status_code, 201, r2.text)
        linea2 = r2.json()["id"]

        r3 = self.client.post(
            f"/personas/conductores?linea_id={linea2}",
            json={"nombre": "Cond Linea2"},
            headers=h,
        )
        self.assertEqual(r3.status_code, 201)

        r4 = self.client.get("/personas/conductores?linea_id=1", headers=h)
        nombres_l1 = [x["nombre"] for x in r4.json()]
        self.assertNotIn("Cond Linea2", nombres_l1)

        r5 = self.client.get(f"/personas/conductores?linea_id={linea2}", headers=h)
        self.assertEqual(len(r5.json()), 1)

        r6 = self.client.delete(f"/lineas/{linea2}", headers=h)
        self.assertEqual(r6.status_code, 400)

        r8 = self.client.delete(
            f"/personas/conductores/{r3.json()['id']}?linea_id={linea2}",
            headers=h,
        )
        self.assertEqual(r8.status_code, 204)
        r9 = self.client.delete(f"/lineas/{linea2}", headers=h)
        self.assertEqual(r9.status_code, 204)

        r10 = self.client.delete("/lineas/1", headers=h)
        self.assertEqual(r10.status_code, 400)


if __name__ == "__main__":
    unittest.main()
