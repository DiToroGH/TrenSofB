"""Sincroniza `acompaniantes_orden` del JSON con los nombres actuales en SQLite."""

from core.services import fusionar_orden_acompaniantes_con_db
from infra import repositories as repo
from infra.migrations import LINEA_SOFB_ID


def fusionar_estado_acompaniantes(estado: dict, linea_id: int = LINEA_SOFB_ID) -> None:
    acompaniantes_db = repo.cargar_acompaniantes(linea_id)
    orden_actual = estado.get("acompaniantes_orden", [])
    estado["acompaniantes_orden"] = fusionar_orden_acompaniantes_con_db(
        orden_actual, acompaniantes_db
    )


def sincronizar_acompaniantes_en_estado_y_guardar(
    linea_id: int = LINEA_SOFB_ID,
) -> dict:
    estado = repo.cargar_estado(linea_id)
    fusionar_estado_acompaniantes(estado, linea_id)
    repo.guardar_estado(estado, linea_id)
    return estado


def persistir_orden_acompaniantes_sqlite_en_estado(
    linea_id: int = LINEA_SOFB_ID,
) -> dict:
    estado = repo.cargar_estado(linea_id)
    fusionar_estado_acompaniantes(estado, linea_id)
    estado["acompaniantes_orden"] = list(repo.cargar_acompaniantes(linea_id))
    repo.guardar_estado(estado, linea_id)
    return estado


def persistir_orden_sqlite_acompaniantes_desde_estado(
    estado: dict, linea_id: int = LINEA_SOFB_ID
) -> None:
    orden = list(estado.get("acompaniantes_orden", []))
    rows = list(repo.listar_personas("acompaniantes", linea_id))
    if not rows:
        return
    by_name = {nombre: (pid, nombre) for pid, nombre in rows}
    ordered: list[tuple[int, str]] = []
    seen: set[str] = set()
    for n in orden:
        if n in by_name:
            ordered.append(by_name[n])
            seen.add(n)
    for pid, nombre in rows:
        if nombre not in seen:
            ordered.append((pid, nombre))
    repo.guardar_orden_personas("acompaniantes", ordered, linea_id)
