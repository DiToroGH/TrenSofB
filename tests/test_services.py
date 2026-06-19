import unittest

from core.services import (
    asignaciones_a_json,
    asignaciones_desde_json,
    conductor_rota_al_cerrar,
    estado_despues_cierre,
    fusionar_orden_acompaniantes_con_db,
    generar_asignacion,
    generar_texto_turno,
    normalizar_locale,
    orden_conductores_para_dia,
    resolver_mensaje_turno,
    resolver_pareja_cierre,
    sanitizar_segundo_acompaniante_estado,
)


class TestAsignacionesJson(unittest.TestCase):
    def test_roundtrip(self):
        raw = [["C1", "A1"], ["C2", "A2"]]
        self.assertEqual(
            asignaciones_a_json(asignaciones_desde_json(raw)),
            raw,
        )


class TestFusionarOrden(unittest.TestCase):
    def test_agrega_faltantes_al_final(self):
        self.assertEqual(
            fusionar_orden_acompaniantes_con_db(["A"], ["A", "B"]),
            ["A", "B"],
        )

    def test_quita_ausentes_y_agrega_nuevos(self):
        self.assertEqual(
            fusionar_orden_acompaniantes_con_db(["X", "A"], ["A", "B"]),
            ["A", "B"],
        )


class TestGenerarTextoTurno(unittest.TestCase):
    def test_es_incluye_conductor_y_acomp(self):
        t = generar_texto_turno("C1", "A1", ["A1", "A2"], locale="es")
        self.assertIn("C1", t)
        self.assertIn("A1", t)
        self.assertIn("pasajero VIP", t)
        self.assertNotIn("replacement", t.lower())
        self.assertNotIn("If you don't", t)

    def test_en_idioma_ingles(self):
        t = generar_texto_turno("C1", "A1", ["A1"], locale="en")
        self.assertIn("tonight", t)
        self.assertIn("VIP passenger is A1", t)
        self.assertNotIn("If you don't", t)

    def test_pt_idioma(self):
        t = generar_texto_turno("C1", "A1", ["A1"], locale="pt")
        self.assertIn("passageiro VIP", t)

    def test_sin_acompaniante(self):
        t = generar_texto_turno("C1", "SIN ACOMPAÑANTE", ["A1"], locale="es")
        self.assertIn("vip asignado", t.lower())

    def test_normalizar_locale(self):
        self.assertEqual(normalizar_locale("en-US"), "en")
        self.assertEqual(normalizar_locale("pt-BR"), "pt")
        self.assertEqual(normalizar_locale(None), "es")


class TestSanitizarSegundoAcompaniante(unittest.TestCase):
    def test_quita_si_es_el_vip(self):
        estado = {
            "acompaniantes_orden": ["A", "B", "C"],
            "segundo_acompanante_hoy": "B",
        }
        sanitizar_segundo_acompaniante_estado(estado, "B", estado["acompaniantes_orden"])
        self.assertNotIn("segundo_acompanante_hoy", estado)

    def test_mantiene_si_es_valido(self):
        estado = {
            "acompaniantes_orden": ["A", "B", "C"],
            "segundo_acompanante_hoy": "C",
        }
        sanitizar_segundo_acompaniante_estado(estado, "A", estado["acompaniantes_orden"])
        self.assertEqual(estado["segundo_acompanante_hoy"], "C")


class TestResolverMensajeTurno(unittest.TestCase):
    def test_usa_mensaje_manual(self):
        estado = {
            "mensaje_turno": "Texto personalizado",
            "mensaje_turno_manual": True,
            "acompaniantes_orden": ["A1"],
        }
        msg = resolver_mensaje_turno(estado, ["C1"], ["A1"], [("C1", "A1")], locale="en")
        self.assertEqual(msg, "Texto personalizado")

    def test_sin_manual_genera_en_idioma(self):
        estado = {"acompaniantes_orden": ["A1", "A2"]}
        msg = resolver_mensaje_turno(
            estado, ["C1"], ["A1", "A2"], [("C1", "A1")], locale="es"
        )
        self.assertIn("pasajero VIP", msg or "")

    def test_mensaje_guardado_sin_manual_regenera(self):
        estado = {
            "mensaje_turno": "Hello old english",
            "acompaniantes_orden": ["A1"],
        }
        msg = resolver_mensaje_turno(estado, ["C1"], ["A1"], [("C1", "A1")], locale="es")
        self.assertIn("pasajero VIP", msg or "")


class TestConductoresFijosSemana(unittest.TestCase):
    def test_domingo_fijo_primero_y_excluido_otros_dias(self):
        cond = ["A", "B", "C", "X"]
        fijos = {"6": "X"}
        domingo = orden_conductores_para_dia(cond, fijos, 6)
        self.assertEqual(domingo[0], "X")
        lunes = orden_conductores_para_dia(cond, fijos, 0)
        self.assertNotIn("X", lunes)


class TestConductorRotaAlCerrar(unittest.TestCase):
    def test_fijo_no_rota(self):
        fijos = {"6": "X"}
        self.assertFalse(conductor_rota_al_cerrar("X", fijos, 6))

    def test_normal_rota(self):
        self.assertTrue(conductor_rota_al_cerrar("A", {}, 0))


class TestGenerarAsignacion(unittest.TestCase):
    def test_asigna_en_orden(self):
        asig, no_disp = generar_asignacion(
            ["C1"], ["A1", "A2"], {"A1", "A2"}
        )
        self.assertEqual(asig, [("C1", "A1")])

    def test_sin_disponibles(self):
        asig, no_disp = generar_asignacion(["C1"], ["A1"], set())
        self.assertEqual(asig[0][1], "SIN ACOMPAÑANTE")


class TestResolverParejaCierre(unittest.TestCase):
    def test_desde_resultados(self):
        c, a = resolver_pareja_cierre([("C1", "A1")], ["C2"], ["A2"])
        self.assertEqual((c, a), ("C1", "A1"))


class TestEstadoDespuesCierre(unittest.TestCase):
    def test_mueve_vip_al_final(self):
        estado = {
            "acompaniantes_orden": ["A", "B", "C"],
            "no_disponibles_hoy": [],
        }
        nuevo = estado_despues_cierre(estado, "C1", "A", "2020-01-02")
        self.assertEqual(nuevo["acompaniantes_orden"][-1], "A")
        self.assertEqual(nuevo["fecha"], "2020-01-02")

    def test_segundo_acompaniante_al_final(self):
        estado = {
            "acompaniantes_orden": ["A", "B", "C"],
            "segundo_acompanante_hoy": "B",
        }
        nuevo = estado_despues_cierre(
            estado, "C1", "A", "2020-01-02", segundo_acompanante_hoy="B"
        )
        self.assertNotIn("segundo_acompanante_hoy", nuevo)
        self.assertEqual(nuevo["acompaniantes_orden"][-1], "B")
