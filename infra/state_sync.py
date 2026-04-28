"""Sincroniza `acompaniantes_orden` del JSON con los nombres actuales en SQLite."""

from core.services import fusionar_orden_acompaniantes_con_db
from infra import repositories as repo


def fusionar_estado_acompaniantes(estado: dict) -> None:
    acompaniantes_db = repo.cargar_acompaniantes()
    orden_actual = estado.get("acompaniantes_orden", [])
    estado["acompaniantes_orden"] = fusionar_orden_acompaniantes_con_db(
        orden_actual, acompaniantes_db
    )


def sincronizar_acompaniantes_en_estado_y_guardar() -> dict:
    estado = repo.cargar_estado()
    fusionar_estado_acompaniantes(estado)
    repo.guardar_estado(estado)
    return estado
