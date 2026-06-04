import unittest

from core.services import (
    asignaciones_a_json,
    asignaciones_desde_json,
    estado_despues_cierre,
    fusionar_orden_acompaniantes_con_db,
    generar_asignacion,
    generar_texto_turno,
    resolver_mensaje_turno,
    resolver_pareja_cierre,
)


class TestAsignacionesJson(unittest.TestCase):
    def test_roundtrip(self):
        orig = [("D1", "A1"), ("D2", "B")]
        self.assertEqual(asignaciones_desde_json(asignaciones_a_json(orig)), orig)

    def test_desde_json_invalido_ignora(self):
        self.assertEqual(
            asignaciones_desde_json([["ok", "x"], "bad", ["only"]]),
            [("ok", "x")],
        )


class TestFusionarOrden(unittest.TestCase):
    def test_agrega_faltantes_al_final(self):
        self.assertEqual(
            fusionar_orden_acompaniantes_con_db(["A"], ["A", "B"]),
            ["A", "B"],
        )

    def test_quita_los_que_ya_no_estan_en_db(self):
        self.assertEqual(
            fusionar_orden_acompaniantes_con_db(["X", "A"], ["A", "B"]),
            ["A", "B"],
        )


class TestGenerarTextoTurno(unittest.TestCase):
    def test_incluye_conductor_y_acomp(self):
        t = generar_texto_turno("C1", "A1", ["A1", "A2", "A3"])
        self.assertIn("C1", t)
        self.assertIn("A1", t)
        self.assertIn("A2", t)
        self.assertIn("A3", t)
        self.assertIn("tonight", t)
        self.assertIn("the replacement are this A2, A3", t)
        self.assertIn("If all three fail", t)

    def test_respaldo_solo_entre_disponibles(self):
        t = generar_texto_turno(
            "C1", "A1", ["A1", "A2", "A3"], disponibles={"A1", "A3"}
        )
        self.assertIn("C1", t)
        self.assertIn("A1", t)
        self.assertIn("A3", t)
        self.assertNotIn("A2", t)
        self.assertIn("the replacement are this A3", t)
        self.assertIn("If all two fail", t)

    def test_formato_lista_larga_respaldos(self):
        orden = [
            "Monicaj",
            "annapine",
            "Bronco972",
            "Flo291990",
            "Borgeess",
            "Solely1",
            "Suki100",
            "AllyCat83",
            "BigH80",
            "JRod89",
        ]
        t = generar_texto_turno("LT Chipman", "annapine", orden)
        self.assertIn("tonight", t)
        self.assertIn("VIP passenger is annapine", t)
        self.assertIn(
            "the replacement are this Bronco972, Flo291990, Borgeess, Solely1, "
            "Suki100, AllyCat83, BigH80, JRod89, Monicaj",
            t,
        )
        self.assertIn("If all ten fail", t)

    def test_maximo_nueve_reemplazos(self):
        orden = ["VIP"] + [f"A{i}" for i in range(1, 16)]
        t = generar_texto_turno("C1", "VIP", orden)
        parte = t.split("the replacement are this ", 1)[1].split(" . If all", 1)[0]
        nombres = [x.strip() for x in parte.split(",")]
        self.assertEqual(len(nombres), 9)
        self.assertEqual(nombres[0], "A1")
        self.assertEqual(nombres[8], "A9")
        self.assertNotIn("A10", t)


class TestResolverMensajeTurno(unittest.TestCase):
    def test_usa_mensaje_guardado(self):
        estado = {
            "mensaje_turno": "Texto personalizado",
            "acompaniantes_orden": ["A1"],
        }
        msg = resolver_mensaje_turno(estado, ["C1"], ["A1"], [("C1", "A1")])
        self.assertEqual(msg, "Texto personalizado")

    def test_sin_guardado_genera_plantilla(self):
        estado = {"acompaniantes_orden": ["A1", "A2"]}
        msg = resolver_mensaje_turno(estado, ["C1"], ["A1", "A2"], [("C1", "A1")])
        self.assertIn("C1", msg or "")
        self.assertIn("A1", msg or "")


class TestGenerarAsignacion(unittest.TestCase):
    def test_todos_disponibles_rotan(self):
        cond = ["D1", "D2"]
        orden = ["A", "B", "C"]
        disp = set(orden)
        asig, nd = generar_asignacion(cond, orden, disp)
        self.assertEqual(asig, [("D1", "A"), ("D2", "B")])
        self.assertEqual(nd, [])

    def test_uno_no_disponible(self):
        cond = ["D1"]
        orden = ["A", "B"]
        asig, nd = generar_asignacion(cond, orden, {"B"})
        self.assertEqual(asig, [("D1", "B")])
        self.assertEqual(nd, ["A"])

    def test_nadie_disponible(self):
        cond = ["D1", "D2"]
        orden = ["A", "B"]
        asig, nd = generar_asignacion(cond, orden, set())
        self.assertEqual(asig, [("D1", "SIN ACOMPAÑANTE"), ("D2", "SIN ACOMPAÑANTE")])
        self.assertEqual(set(nd), {"A", "B"})


class TestCierre(unittest.TestCase):
    def test_resolver_desde_resultados(self):
        self.assertEqual(
            resolver_pareja_cierre([("D", "A")], ["D2"], ["X"]),
            ("D", "A"),
        )

    def test_resolver_sin_resultados(self):
        self.assertEqual(
            resolver_pareja_cierre([], ["D1", "D2"], ["A1", "A2"]),
            ("D1", "A1"),
        )

    def test_estado_despues_cierre_mueve_no_disp_al_frente_y_acomp_al_final(self):
        estado = {
            "fecha": "2020-01-01",
            "acompaniantes_orden": ["A", "B", "C"],
            "no_disponibles_hoy": ["B"],
        }
        nuevo = estado_despues_cierre(estado, "D", "A", "2020-01-02")
        self.assertEqual(nuevo["acompaniantes_orden"], ["B", "C", "A"])
        self.assertEqual(nuevo["no_disponibles_hoy"], [])
        self.assertEqual(nuevo["fecha"], "2020-01-02")

    def test_estado_despues_cierre_segundo_acomp_al_final(self):
        estado = {
            "fecha": "2020-01-01",
            "acompaniantes_orden": ["A", "B", "C"],
            "no_disponibles_hoy": [],
            "segundo_acompanante_hoy": "B",
        }
        nuevo = estado_despues_cierre(
            estado, "D", "A", "2020-01-02", segundo_acompanante_hoy="B"
        )
        self.assertEqual(nuevo["acompaniantes_orden"], ["C", "A", "B"])
        self.assertNotIn("segundo_acompanante_hoy", nuevo)


if __name__ == "__main__":
    unittest.main()
