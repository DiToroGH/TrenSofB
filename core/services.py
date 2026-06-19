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


def normalizar_locale(locale: str | None) -> str:
    if not locale:
        return "es"
    loc = str(locale).strip().lower()
    if loc.startswith("pt"):
        return "pt"
    if loc.startswith("en"):
        return "en"
    return "es"


_TURN_MSG_VIP = {
    "es": (
        "Hola {conductor}, hoy te toca conducir el tren y tu pasajero VIP es {acomp}. "
        "Contactalo con anticipación para coordinar horarios. Di Toro."
    ),
    "en": (
        "Hello {conductor}, tonight it's your turn to drive the train, and your VIP "
        "passenger is {acomp}. Try to contact them ahead of time and coordinate the "
        "schedule so they'll be ready. Di Toro."
    ),
    "pt": (
        "Olá {conductor}, hoje é sua vez de conduzir o trem e seu passageiro VIP é "
        "{acomp}. Entre em contato com antecedência para combinar horários. Di Toro."
    ),
}

_TURN_MSG_SIN_VIP = {
    "es": (
        "Hola {conductor}, hoy te toca conducir el tren sin acompañante VIP asignado. "
        "Di Toro."
    ),
    "en": (
        "Hello {conductor}, tonight it's your turn to drive the train with no VIP "
        "companion assigned. Di Toro."
    ),
    "pt": (
        "Olá {conductor}, hoje é sua vez de conduzir o trem sem acompanhante VIP "
        "atribuído. Di Toro."
    ),
}


def generar_texto_turno(
    conductor: str,
    acomp: str,
    orden_acompaniantes: list[str],
    *,
    disponibles: set[str] | frozenset[str] | None = None,
    locale: str | None = None,
) -> str:
    """Plantilla del mensaje de turno (sin lista de reemplazos)."""
    _ = orden_acompaniantes, disponibles
    loc = normalizar_locale(locale)
    if not str(acomp or "").strip() or acomp == "SIN ACOMPAÑANTE":
        return _TURN_MSG_SIN_VIP[loc].format(conductor=conductor)
    return _TURN_MSG_VIP[loc].format(conductor=conductor, acomp=acomp)


def calcular_mensaje_turno_automatico(
    conductores: list[str],
    orden_acompaniantes: list[str],
    resultados: list[tuple[str, str]],
    *,
    disponibles: set[str] | frozenset[str] | None = None,
    locale: str | None = None,
) -> str | None:
    if resultados:
        c, a = resultados[0]
        return generar_texto_turno(
            c, a, orden_acompaniantes, disponibles=disponibles, locale=locale
        )
    if conductores and orden_acompaniantes:
        return generar_texto_turno(
            conductores[0],
            orden_acompaniantes[0],
            orden_acompaniantes,
            disponibles=disponibles,
            locale=locale,
        )
    return None


def resolver_mensaje_turno(
    estado: dict,
    conductores: list[str],
    orden_acompaniantes: list[str],
    resultados: list[tuple[str, str]],
    *,
    locale: str | None = None,
) -> str | None:
    """Mensaje editado manualmente, o plantilla automática en el idioma pedido."""
    if estado.get("mensaje_turno_manual"):
        guardado = estado.get("mensaje_turno")
        if isinstance(guardado, str) and guardado.strip():
            return guardado.strip()
    raw_disp = estado.get("disponibles_hoy")
    disp_msg = set(raw_disp) if isinstance(raw_disp, list) else None
    return calcular_mensaje_turno_automatico(
        conductores,
        orden_acompaniantes,
        resultados,
        disponibles=disp_msg,
        locale=locale,
    )


def normalizar_fijos_semana(raw: dict | None) -> dict[int, str]:
    """Claves 0–6 (lunes–domingo, estilo `date.weekday()`)."""
    if not raw:
        return {}
    out: dict[int, str] = {}
    for key, nombre in raw.items():
        try:
            dia = int(key)
        except (TypeError, ValueError):
            continue
        if 0 <= dia <= 6:
            n = str(nombre or "").strip()
            if n:
                out[dia] = n
    return out


def orden_conductores_para_dia(
    conductores: list[str],
    fijos_semana: dict[int, str] | dict | None,
    weekday: int,
) -> list[str]:
    """
    Orden de conductores activos en un día: el fijo del día primero;
    el resto rota sin incluir conductores fijados en otros días.
    """
    fijos = (
        fijos_semana
        if fijos_semana and all(isinstance(k, int) for k in fijos_semana)
        else normalizar_fijos_semana(fijos_semana)
    )
    fijo_hoy = fijos.get(weekday)
    excluir = {n for d, n in fijos.items() if d != weekday}
    rotadores = [c for c in conductores if c not in excluir]
    if fijo_hoy and fijo_hoy in conductores:
        rotadores = [c for c in rotadores if c != fijo_hoy]
        return [fijo_hoy] + rotadores
    return rotadores


def conductor_rota_al_cerrar(
    conductor: str | None,
    fijos_semana: dict[int, str] | dict | None,
    weekday: int,
) -> bool:
    """False si el conductor está fijado ese día de la semana (no pasa al final)."""
    if not conductor:
        return False
    fijos = (
        fijos_semana
        if fijos_semana and all(isinstance(k, int) for k in fijos_semana)
        else normalizar_fijos_semana(fijos_semana)
    )
    return fijos.get(weekday) != conductor


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


def sanitizar_segundo_acompaniante_estado(
    estado: dict,
    vip: str | None,
    orden_acompaniantes: list[str] | None = None,
) -> None:
    """Quita segundo acompañante si coincide con el VIP o ya no es válido."""
    raw = estado.get("segundo_acompanante_hoy")
    if raw is None:
        return
    segundo = str(raw).strip()
    if not segundo:
        estado.pop("segundo_acompanante_hoy", None)
        return
    orden = list(orden_acompaniantes or estado.get("acompaniantes_orden") or [])
    vip_ok = vip if vip and vip != "SIN ACOMPAÑANTE" else None
    if (vip_ok and segundo == vip_ok) or segundo not in orden:
        estado.pop("segundo_acompanante_hoy", None)


def resolver_pareja_cierre(
    resultados: list[tuple[str, str]],
    conductores: list[str],
    acompaniantes_orden: list[str],
    *,
    weekday: int | None = None,
    fijos_semana: dict[int, str] | dict | None = None,
) -> tuple[str | None, str | None]:
    if resultados:
        return resultados[0][0], resultados[0][1]
    if weekday is not None:
        orden_cond = orden_conductores_para_dia(conductores, fijos_semana, weekday)
        conductor_hoy = orden_cond[0] if orden_cond else None
    else:
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
