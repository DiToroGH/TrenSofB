"""CRUD y orden de conductores / acompañantes (misma DB que el escritorio)."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from api.deps import get_linea_id
from infra import repositories as repo
from infra.state_sync import (
    persistir_orden_acompaniantes_sqlite_en_estado,
    sincronizar_acompaniantes_en_estado_y_guardar,
)
from core.auth import TokenData, get_current_user, is_admin

router = APIRouter(prefix="/personas", tags=["personas"])


class PersonaOut(BaseModel):
    id: int
    nombre: str


class PersonaNombreBody(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)


class PersonaNombreUpdateBody(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)


class MoverBody(BaseModel):
    persona_id: int
    direccion: int = Field(..., description="-1 subir, +1 bajar")


class MoverExtremoBody(BaseModel):
    persona_id: int
    al_inicio: bool


class CargaMasivaBody(BaseModel):
    texto: str = Field(
        ...,
        description="Un nombre por línea; vacías se ignoran.",
    )


class CargaMasivaResponse(BaseModel):
    agregados: int
    duplicados: int
    errores: int


def _tabla_conductores() -> str:
    return "conductores"


def _tabla_acompaniantes() -> str:
    return "acompaniantes"


def _listar(tabla: str, linea_id: int) -> list[PersonaOut]:
    return [
        PersonaOut(id=row[0], nombre=row[1])
        for row in repo.listar_personas(tabla, linea_id)
    ]


def _mover_vecino(tabla: str, persona_id: int, direccion: int, linea_id: int) -> None:
    items = list(repo.listar_personas(tabla, linea_id))
    idx = next((i for i, (pid, _) in enumerate(items) if pid == persona_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Registro no encontrado.")
    nuevo_idx = idx + direccion
    if nuevo_idx < 0 or nuevo_idx >= len(items):
        raise HTTPException(status_code=400, detail="No se puede mover en esa dirección.")
    items[idx], items[nuevo_idx] = items[nuevo_idx], items[idx]
    repo.guardar_orden_personas(tabla, items, linea_id)


def _mover_extremo(tabla: str, persona_id: int, al_inicio: bool, linea_id: int) -> None:
    items = list(repo.listar_personas(tabla, linea_id))
    idx = next((i for i, (pid, _) in enumerate(items) if pid == persona_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Registro no encontrado.")
    movido = items.pop(idx)
    if al_inicio:
        items.insert(0, movido)
    else:
        items.append(movido)
    repo.guardar_orden_personas(tabla, items, linea_id)


# --- Conductores ---


@router.get("/conductores", response_model=list[PersonaOut])
def listar_conductores(linea_id: int = Depends(get_linea_id)):
    return _listar(_tabla_conductores(), linea_id)


@router.post("/conductores", response_model=PersonaOut, status_code=201)
def alta_conductor(
    body: PersonaNombreBody,
    current_user: TokenData = Depends(get_current_user),
    linea_id: int = Depends(get_linea_id),
):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores pueden agregar conductores")
    try:
        repo.insertar_persona(_tabla_conductores(), body.nombre.strip(), linea_id)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Ese nombre ya existe.")
    items = repo.listar_personas(_tabla_conductores(), linea_id)
    ultimo = items[-1]
    return PersonaOut(id=ultimo[0], nombre=ultimo[1])


@router.patch("/conductores/{persona_id}", response_model=PersonaOut)
def editar_conductor(
    persona_id: int,
    body: PersonaNombreUpdateBody,
    current_user: TokenData = Depends(get_current_user),
    linea_id: int = Depends(get_linea_id),
):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores pueden editar conductores")
    try:
        repo.editar_persona(_tabla_conductores(), persona_id, body.nombre.strip(), linea_id)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Ese nombre ya existe.")
    for row in repo.listar_personas(_tabla_conductores(), linea_id):
        if row[0] == persona_id:
            return PersonaOut(id=row[0], nombre=row[1])
    raise HTTPException(status_code=404, detail="Registro no encontrado.")


@router.delete("/conductores/{persona_id}", status_code=204)
def borrar_conductor(
    persona_id: int,
    current_user: TokenData = Depends(get_current_user),
    linea_id: int = Depends(get_linea_id),
):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar conductores")
    repo.borrar_persona(_tabla_conductores(), persona_id, linea_id)


@router.post("/conductores/mover", status_code=204)
def mover_conductor(
    body: MoverBody,
    current_user: TokenData = Depends(get_current_user),
    linea_id: int = Depends(get_linea_id),
):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores pueden mover conductores")
    _mover_vecino(_tabla_conductores(), body.persona_id, body.direccion, linea_id)


@router.post("/conductores/mover-extremo", status_code=204)
def mover_conductor_extremo(
    body: MoverExtremoBody,
    current_user: TokenData = Depends(get_current_user),
    linea_id: int = Depends(get_linea_id),
):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores pueden mover conductores")
    _mover_extremo(_tabla_conductores(), body.persona_id, body.al_inicio, linea_id)


# --- Acompañantes ---


@router.get("/acompaniantes", response_model=list[PersonaOut])
def listar_acompaniantes(linea_id: int = Depends(get_linea_id)):
    return _listar(_tabla_acompaniantes(), linea_id)


@router.post("/acompaniantes", response_model=PersonaOut, status_code=201)
def alta_acompaniante(
    body: PersonaNombreBody,
    current_user: TokenData = Depends(get_current_user),
    linea_id: int = Depends(get_linea_id),
):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores pueden agregar acompañantes")
    try:
        repo.insertar_persona(_tabla_acompaniantes(), body.nombre.strip(), linea_id)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Ese nombre ya existe.")
    sincronizar_acompaniantes_en_estado_y_guardar(linea_id)
    items = repo.listar_personas(_tabla_acompaniantes(), linea_id)
    ultimo = items[-1]
    return PersonaOut(id=ultimo[0], nombre=ultimo[1])


@router.patch("/acompaniantes/{persona_id}", response_model=PersonaOut)
def editar_acompaniante(
    persona_id: int,
    body: PersonaNombreUpdateBody,
    current_user: TokenData = Depends(get_current_user),
    linea_id: int = Depends(get_linea_id),
):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores pueden editar acompañantes")
    try:
        repo.editar_persona(_tabla_acompaniantes(), persona_id, body.nombre.strip(), linea_id)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Ese nombre ya existe.")
    sincronizar_acompaniantes_en_estado_y_guardar(linea_id)
    for row in repo.listar_personas(_tabla_acompaniantes(), linea_id):
        if row[0] == persona_id:
            return PersonaOut(id=row[0], nombre=row[1])
    raise HTTPException(status_code=404, detail="Registro no encontrado.")


@router.delete("/acompaniantes/{persona_id}", status_code=204)
def borrar_acompaniante(
    persona_id: int,
    current_user: TokenData = Depends(get_current_user),
    linea_id: int = Depends(get_linea_id),
):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar acompañantes")
    repo.borrar_persona(_tabla_acompaniantes(), persona_id, linea_id)
    sincronizar_acompaniantes_en_estado_y_guardar(linea_id)


@router.post("/acompaniantes/mover", status_code=204)
def mover_acompaniante(
    body: MoverBody,
    current_user: TokenData = Depends(get_current_user),
    linea_id: int = Depends(get_linea_id),
):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores pueden mover acompañantes")
    _mover_vecino(_tabla_acompaniantes(), body.persona_id, body.direccion, linea_id)
    persistir_orden_acompaniantes_sqlite_en_estado(linea_id)


@router.post("/acompaniantes/mover-extremo", status_code=204)
def mover_acompaniante_extremo(
    body: MoverExtremoBody,
    current_user: TokenData = Depends(get_current_user),
    linea_id: int = Depends(get_linea_id),
):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores pueden mover acompañantes")
    _mover_extremo(_tabla_acompaniantes(), body.persona_id, body.al_inicio, linea_id)
    persistir_orden_acompaniantes_sqlite_en_estado(linea_id)


@router.post("/acompaniantes/carga-masiva", response_model=CargaMasivaResponse)
def carga_masiva_acompaniantes(
    body: CargaMasivaBody,
    current_user: TokenData = Depends(get_current_user),
    linea_id: int = Depends(get_linea_id),
):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores pueden cargar masivamente acompañantes")
    candidatos = [x.strip() for x in body.texto.splitlines() if x.strip()]
    agregados = 0
    duplicados = 0
    errores = 0
    vistos: set[str] = set()
    for nombre in candidatos:
        clave = nombre.casefold()
        if clave in vistos:
            duplicados += 1
            continue
        vistos.add(clave)
        try:
            repo.insertar_persona(_tabla_acompaniantes(), nombre, linea_id)
            agregados += 1
        except sqlite3.IntegrityError:
            duplicados += 1
        except sqlite3.Error:
            errores += 1
    sincronizar_acompaniantes_en_estado_y_guardar(linea_id)
    return CargaMasivaResponse(agregados=agregados, duplicados=duplicados, errores=errores)
