"""CRUD y orden de conductores / acompañantes (misma DB que el escritorio)."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from infra import repositories as repo
from infra.state_sync import sincronizar_acompaniantes_en_estado_y_guardar
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


def _listar(tabla: str) -> list[PersonaOut]:
    return [PersonaOut(id=row[0], nombre=row[1]) for row in repo.listar_personas(tabla)]


def _mover_vecino(tabla: str, persona_id: int, direccion: int) -> None:
    items = list(repo.listar_personas(tabla))
    idx = next((i for i, (pid, _) in enumerate(items) if pid == persona_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Registro no encontrado.")
    nuevo_idx = idx + direccion
    if nuevo_idx < 0 or nuevo_idx >= len(items):
        raise HTTPException(status_code=400, detail="No se puede mover en esa dirección.")
    items[idx], items[nuevo_idx] = items[nuevo_idx], items[idx]
    repo.guardar_orden_personas(tabla, items)


def _mover_extremo(tabla: str, persona_id: int, al_inicio: bool) -> None:
    items = list(repo.listar_personas(tabla))
    idx = next((i for i, (pid, _) in enumerate(items) if pid == persona_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Registro no encontrado.")
    movido = items.pop(idx)
    if al_inicio:
        items.insert(0, movido)
    else:
        items.append(movido)
    repo.guardar_orden_personas(tabla, items)


# --- Conductores ---


@router.get("/conductores", response_model=list[PersonaOut])
def listar_conductores():
    return _listar(_tabla_conductores())


@router.post("/conductores", response_model=PersonaOut, status_code=201)
def alta_conductor(body: PersonaNombreBody, current_user: TokenData = Depends(get_current_user)):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores pueden agregar conductores")
    try:
        repo.insertar_persona(_tabla_conductores(), body.nombre.strip())
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Ese nombre ya existe.")
    items = repo.listar_personas(_tabla_conductores())
    ultimo = items[-1]
    return PersonaOut(id=ultimo[0], nombre=ultimo[1])


@router.patch("/conductores/{persona_id}", response_model=PersonaOut)
def editar_conductor(persona_id: int, body: PersonaNombreUpdateBody, current_user: TokenData = Depends(get_current_user)):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores pueden editar conductores")
    try:
        repo.editar_persona(_tabla_conductores(), persona_id, body.nombre.strip())
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Ese nombre ya existe.")
    for row in repo.listar_personas(_tabla_conductores()):
        if row[0] == persona_id:
            return PersonaOut(id=row[0], nombre=row[1])
    raise HTTPException(status_code=404, detail="Registro no encontrado.")


@router.delete("/conductores/{persona_id}", status_code=204)
def borrar_conductor(persona_id: int, current_user: TokenData = Depends(get_current_user)):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar conductores")
    repo.borrar_persona(_tabla_conductores(), persona_id)


@router.post("/conductores/mover", status_code=204)
def mover_conductor(body: MoverBody, current_user: TokenData = Depends(get_current_user)):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores pueden mover conductores")
    _mover_vecino(_tabla_conductores(), body.persona_id, body.direccion)


@router.post("/conductores/mover-extremo", status_code=204)
def mover_conductor_extremo(body: MoverExtremoBody, current_user: TokenData = Depends(get_current_user)):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores pueden mover conductores")
    _mover_extremo(_tabla_conductores(), body.persona_id, body.al_inicio)


# --- Acompañantes ---


@router.get("/acompaniantes", response_model=list[PersonaOut])
def listar_acompaniantes():
    return _listar(_tabla_acompaniantes())


@router.post("/acompaniantes", response_model=PersonaOut, status_code=201)
def alta_acompaniante(body: PersonaNombreBody, current_user: TokenData = Depends(get_current_user)):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores pueden agregar acompañantes")
    try:
        repo.insertar_persona(_tabla_acompaniantes(), body.nombre.strip())
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Ese nombre ya existe.")
    sincronizar_acompaniantes_en_estado_y_guardar()
    items = repo.listar_personas(_tabla_acompaniantes())
    ultimo = items[-1]
    return PersonaOut(id=ultimo[0], nombre=ultimo[1])


@router.patch("/acompaniantes/{persona_id}", response_model=PersonaOut)
def editar_acompaniante(persona_id: int, body: PersonaNombreUpdateBody, current_user: TokenData = Depends(get_current_user)):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores pueden editar acompañantes")
    try:
        repo.editar_persona(_tabla_acompaniantes(), persona_id, body.nombre.strip())
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Ese nombre ya existe.")
    sincronizar_acompaniantes_en_estado_y_guardar()
    for row in repo.listar_personas(_tabla_acompaniantes()):
        if row[0] == persona_id:
            return PersonaOut(id=row[0], nombre=row[1])
    raise HTTPException(status_code=404, detail="Registro no encontrado.")


@router.delete("/acompaniantes/{persona_id}", status_code=204)
def borrar_acompaniante(persona_id: int, current_user: TokenData = Depends(get_current_user)):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar acompañantes")
    repo.borrar_persona(_tabla_acompaniantes(), persona_id)
    sincronizar_acompaniantes_en_estado_y_guardar()


@router.post("/acompaniantes/mover", status_code=204)
def mover_acompaniante(body: MoverBody, current_user: TokenData = Depends(get_current_user)):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores pueden mover acompañantes")
    _mover_vecino(_tabla_acompaniantes(), body.persona_id, body.direccion)
    sincronizar_acompaniantes_en_estado_y_guardar()


@router.post("/acompaniantes/mover-extremo", status_code=204)
def mover_acompaniante_extremo(body: MoverExtremoBody, current_user: TokenData = Depends(get_current_user)):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores pueden mover acompañantes")
    _mover_extremo(_tabla_acompaniantes(), body.persona_id, body.al_inicio)
    sincronizar_acompaniantes_en_estado_y_guardar()


@router.post("/acompaniantes/carga-masiva", response_model=CargaMasivaResponse)
def carga_masiva_acompaniantes(body: CargaMasivaBody, current_user: TokenData = Depends(get_current_user)):
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
            repo.insertar_persona(_tabla_acompaniantes(), nombre)
            agregados += 1
        except sqlite3.IntegrityError:
            duplicados += 1
        except sqlite3.Error:
            errores += 1
    sincronizar_acompaniantes_en_estado_y_guardar()
    return CargaMasivaResponse(agregados=agregados, duplicados=duplicados, errores=errores)
