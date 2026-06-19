"""Dependencias compartidas de la API."""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Query

from core.auth import TokenData, get_current_user, is_admin
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


def get_linea_id_for_user(
    linea_id: int = Depends(get_linea_id),
    current_user: TokenData = Depends(get_current_user),
) -> int:
    if not is_admin(current_user) and not repo.linea_es_visible(linea_id):
        raise HTTPException(status_code=403, detail="Línea no disponible.")
    return linea_id


def get_locale(
    lang: str | None = Query(None, description="Idioma de la interfaz (es, en, pt)"),
    x_lang: str | None = Header(None, alias="X-Lang"),
) -> str:
    raw = (lang or x_lang or "es").strip().lower()
    if raw.startswith("pt"):
        return "pt"
    if raw.startswith("en"):
        return "en"
    return "es"
