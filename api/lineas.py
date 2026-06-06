"""CRUD de líneas de transporte."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.deps import get_linea_id
from core.auth import TokenData, get_current_user, is_admin
from infra import repositories as repo
from infra.migrations import LINEA_SOFB_ID

router = APIRouter(prefix="/lineas", tags=["lineas"])


class LineaOut(BaseModel):
    id: int
    nombre: str


class LineaCreateBody(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)


class LineaUpdateBody(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)


@router.get("", response_model=list[LineaOut])
def listar_lineas_endpoint(current_user: TokenData = Depends(get_current_user)):
    _ = current_user
    return [LineaOut(id=lid, nombre=nombre) for lid, nombre in repo.listar_lineas()]


@router.post("", response_model=LineaOut, status_code=201)
def crear_linea_endpoint(
    body: LineaCreateBody,
    current_user: TokenData = Depends(get_current_user),
):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores pueden crear líneas.")
    try:
        linea_id = repo.crear_linea(body.nombre.strip())
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Ya existe una línea con ese nombre.")
    repo.inicializar_estado_linea(linea_id)
    info = repo.obtener_linea(linea_id)
    assert info is not None
    return LineaOut(id=info[0], nombre=info[1])


@router.patch("/{linea_id}", response_model=LineaOut)
def renombrar_linea_endpoint(
    linea_id: int,
    body: LineaUpdateBody,
    current_user: TokenData = Depends(get_current_user),
):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores pueden renombrar líneas.")
    if not repo.linea_existe(linea_id):
        raise HTTPException(status_code=404, detail="Línea no encontrada.")
    try:
        repo.renombrar_linea(linea_id, body.nombre.strip())
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Ya existe una línea con ese nombre.")
    info = repo.obtener_linea(linea_id)
    assert info is not None
    return LineaOut(id=info[0], nombre=info[1])


@router.delete("/{linea_id}", status_code=204)
def borrar_linea_endpoint(
    linea_id: int,
    current_user: TokenData = Depends(get_current_user),
):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar líneas.")
    if linea_id == LINEA_SOFB_ID:
        raise HTTPException(status_code=400, detail="No se puede eliminar la línea SofB.")
    if not repo.linea_existe(linea_id):
        raise HTTPException(status_code=404, detail="Línea no encontrada.")
    try:
        repo.borrar_linea(linea_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/actual", response_model=LineaOut)
def linea_actual(linea_id: int = Depends(get_linea_id)):
    info = repo.obtener_linea(linea_id)
    if info is None:
        raise HTTPException(status_code=404, detail="Línea no encontrada.")
    return LineaOut(id=info[0], nombre=info[1])
