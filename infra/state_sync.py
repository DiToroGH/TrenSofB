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


def persistir_orden_acompaniantes_sqlite_en_estado() -> dict:
    """Tras reordenar en SQLite (subir/bajar/inicio/final), copia ese orden a `acompaniantes_orden` en JSON."""
    estado = repo.cargar_estado()
    fusionar_estado_acompaniantes(estado)
    estado["acompaniantes_orden"] = list(repo.cargar_acompaniantes())
    repo.guardar_estado(estado)
    return estado


def persistir_orden_sqlite_acompaniantes_desde_estado(estado: dict) -> None:
    """Tras guardar un `acompaniantes_orden` nuevo en JSON (p. ej. cierre de día), alinea la columna `orden` en SQLite."""
    orden = list(estado.get("acompaniantes_orden", []))
    rows = list(repo.listar_personas("acompaniantes"))
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
    repo.guardar_orden_personas("acompaniantes", ordered)
