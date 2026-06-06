"""Dependencias compartidas de la API."""

from __future__ import annotations

from fastapi import Header, HTTPException, Query

from infra import repositories as repo
from infra.migrations import LINEA_SOFB_ID


def get_linea_id(
    linea_id: int | None = Query(None, description="ID de línea de transporte"),
    x_linea_id: int | None = Header(None, alias="X-Linea-Id"),
) -> int:
    lid = linea_id if linea_id is not None else x_linea_id
    if lid is None:
        lid = LINEA_SOFB_ID
    if lid < 1 or not repo.linea_existe(lid):
        raise HTTPException(status_code=404, detail="Línea no encontrada.")
    return lid
