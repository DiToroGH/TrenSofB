"""Reglas de negocio puras (sin Tkinter ni I/O)."""

from __future__ import annotations


def asignaciones_a_json(asignaciones: list[tuple[str, str]]) -> list[list[str]]:
    return [[c, a] for c, a in asignaciones]


def asignaciones_desde_json(raw: list | None) -> list[tuple[str, str]]:
    if not raw:
        return []
    out: list[tuple[str, str]] = []
    for item in raw:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            out.append((str(item[0]), str(item[1])))
    return out


def fusionar_orden_acompaniantes_con_db(
    orden_actual: list[str], acompaniantes_db: list[str]
) -> list[str]:
    faltantes = [a for a in acompaniantes_db if a not in orden_actual]
    return [a for a in orden_actual if a in acompaniantes_db] + faltantes


def generar_texto_turno(
    conductor: str,
    acomp: str,
    orden_acompaniantes: list[str],
    *,
    disponibles: set[str] | frozenset[str] | None = None,
) -> str:
    """Si `disponibles` no es None, respaldos 2 y 3 solo recorren gente marcada disponible hoy."""
    orden = list(orden_acompaniantes)
    if disponibles is not None:
        circulo = [x for x in orden if x in disponibles]
    else:
        circulo = orden

    respaldo_1 = acomp
    respaldo_2 = acomp
    if circulo:
        try:
            idx = circulo.index(acomp)
        except ValueError:
            idx = 0
        n = len(circulo)
        respaldo_1 = circulo[(idx + 1) % n]
        respaldo_2 = circulo[(idx + 2) % n]
    return (
        f'Hello {conductor} , tomorrow it\'s your turn to drive the train, and your VIP passenger is '
        f'"{acomp}" . Try to contact him ahead of time and coordinate the schedule so he\'ll be ready. '
        f'If you don\'t get a response from {acomp}, the replacement is {respaldo_1}. '
        f'If neither of them responds, the third person to contact is {respaldo_2}. '
        "If all three fail, let me know 😅. Di Toro."
    )


def generar_asignacion(
    conductores: list[str],
    orden_acompaniantes: list[str],
    disponibles: set[str],
) -> tuple[list[tuple[str, str]], list[str]]:
    orden = orden_acompaniantes[:]
    idx = 0
    no_disponibles_hoy: list[str] = []
    asignaciones: list[tuple[str, str]] = []
    for conductor in conductores:
        intentos = 0
        asignado = False
        while intentos < len(orden):
            acomp = orden[idx]
            if acomp in disponibles:
                asignaciones.append((conductor, acomp))
                idx = (idx + 1) % len(orden)
                asignado = True
                break
            no_disponibles_hoy.append(acomp)
            idx = (idx + 1) % len(orden)
            intentos += 1
        if not asignado:
            asignaciones.append((conductor, "SIN ACOMPAÑANTE"))
    return asignaciones, list(dict.fromkeys(no_disponibles_hoy))


def resolver_pareja_cierre(
    resultados: list[tuple[str, str]],
    conductores: list[str],
    acompaniantes_orden: list[str],
) -> tuple[str | None, str | None]:
    if resultados:
        return resultados[0][0], resultados[0][1]
    conductor_hoy = conductores[0] if conductores else None
    acomp_hoy = acompaniantes_orden[0] if acompaniantes_orden else None
    return conductor_hoy, acomp_hoy


def estado_despues_cierre(
    estado: dict,
    conductor_hoy: str | None,
    acomp_hoy: str | None,
    fecha: str,
) -> dict:
    nuevo = {**estado, "acompaniantes_orden": list(estado.get("acompaniantes_orden", []))}
    nd = list(estado.get("no_disponibles_hoy", []))
    actual = nuevo["acompaniantes_orden"]
    resto = [x for x in actual if x not in nd]
    nuevo["acompaniantes_orden"] = nd + resto
    if (
        acomp_hoy
        and acomp_hoy != "SIN ACOMPAÑANTE"
        and acomp_hoy in nuevo["acompaniantes_orden"]
    ):
        nuevo["acompaniantes_orden"].remove(acomp_hoy)
        nuevo["acompaniantes_orden"].append(acomp_hoy)
    nuevo["fecha"] = fecha
    nuevo["no_disponibles_hoy"] = []
    return nuevo
