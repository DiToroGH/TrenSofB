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


MAX_RESPALDOS_MENSAJE = 9

_ENGLISH_COUNT_WORDS: dict[int, str] = {
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
    11: "eleven",
    12: "twelve",
}


def _respaldos_en_orden(acomp: str, circulo: list[str]) -> list[str]:
    """Hasta 9 reemplazos en orden circular después del VIP (sin repetir al VIP)."""
    if not circulo:
        return []
    if acomp == "SIN ACOMPAÑANTE" or acomp not in circulo:
        return list(circulo)[:MAX_RESPALDOS_MENSAJE]
    if len(circulo) == 1:
        return []
    idx = circulo.index(acomp)
    n = len(circulo)
    todos = [circulo[(idx + k) % n] for k in range(1, n)]
    return todos[:MAX_RESPALDOS_MENSAJE]


def _total_contactos_fallo(acomp: str, respaldos: list[str]) -> int:
    if acomp and acomp != "SIN ACOMPAÑANTE":
        return 1 + len(respaldos)
    return len(respaldos)


def generar_texto_turno(
    conductor: str,
    acomp: str,
    orden_acompaniantes: list[str],
    *,
    disponibles: set[str] | frozenset[str] | None = None,
) -> str:
    """Si `disponibles` no es None, la lista de reemplazos solo incluye gente disponible hoy."""
    orden = list(orden_acompaniantes)
    if disponibles is not None:
        circulo = [x for x in orden if x in disponibles]
    else:
        circulo = orden

    respaldos = _respaldos_en_orden(acomp, circulo)
    lista_respaldos = ", ".join(respaldos)
    total = _total_contactos_fallo(acomp, respaldos)
    total_word = _ENGLISH_COUNT_WORDS.get(total, str(total))

    cuerpo = (
        f"Hello {conductor} , tonight it's your turn to drive the train, and your VIP passenger is "
        f"{acomp} . Try to contact them ahead of time and coordinate the schedule so they'll be ready. "
    )
    if respaldos:
        cuerpo += (
            f"If you don't get a response from {acomp}, the replacement are this {lista_respaldos} . "
            f"If all {total_word} fail, let me know 😅. Di Toro."
        )
    else:
        cuerpo += f"If you don't get a response from {acomp}, let me know 😅. Di Toro."
    return cuerpo


def calcular_mensaje_turno_automatico(
    conductores: list[str],
    orden_acompaniantes: list[str],
    resultados: list[tuple[str, str]],
    *,
    disponibles: set[str] | frozenset[str] | None = None,
) -> str | None:
    if resultados:
        c, a = resultados[0]
        return generar_texto_turno(c, a, orden_acompaniantes, disponibles=disponibles)
    if conductores and orden_acompaniantes:
        return generar_texto_turno(
            conductores[0], orden_acompaniantes[0], orden_acompaniantes, disponibles=disponibles
        )
    return None


def resolver_mensaje_turno(
    estado: dict,
    conductores: list[str],
    orden_acompaniantes: list[str],
    resultados: list[tuple[str, str]],
) -> str | None:
    """Mensaje guardado en estado, o plantilla automática si no hay uno personalizado."""
    guardado = estado.get("mensaje_turno")
    if isinstance(guardado, str) and guardado.strip():
        return guardado.strip()
    raw_disp = estado.get("disponibles_hoy")
    disp_msg = set(raw_disp) if isinstance(raw_disp, list) else None
    return calcular_mensaje_turno_automatico(
        conductores, orden_acompaniantes, resultados, disponibles=disp_msg
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


def _mover_acompaniante_al_final(orden: list[str], nombre: str | None) -> None:
    if (
        nombre
        and nombre != "SIN ACOMPAÑANTE"
        and nombre in orden
    ):
        orden.remove(nombre)
        orden.append(nombre)


def estado_despues_cierre(
    estado: dict,
    conductor_hoy: str | None,
    acomp_hoy: str | None,
    fecha: str,
    *,
    segundo_acompanante_hoy: str | None = None,
) -> dict:
    nuevo = {**estado, "acompaniantes_orden": list(estado.get("acompaniantes_orden", []))}
    nd = list(estado.get("no_disponibles_hoy", []))
    actual = nuevo["acompaniantes_orden"]
    resto = [x for x in actual if x not in nd]
    nuevo["acompaniantes_orden"] = nd + resto
    _mover_acompaniante_al_final(nuevo["acompaniantes_orden"], acomp_hoy)
    _mover_acompaniante_al_final(nuevo["acompaniantes_orden"], segundo_acompanante_hoy)
    nuevo["fecha"] = fecha
    nuevo["no_disponibles_hoy"] = []
    nuevo.pop("segundo_acompanante_hoy", None)
    return nuevo
