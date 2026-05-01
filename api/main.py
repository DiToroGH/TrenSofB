"""API REST mínima: mismo estado JSON + SQLite que `app_tren.py`."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.services import (
    asignaciones_a_json,
    asignaciones_desde_json,
    estado_despues_cierre,
    generar_asignacion,
    generar_texto_turno,
    resolver_pareja_cierre,
)
from core.auth import (
    authenticate_user,
    create_access_token,
    verify_token,
    TokenData,
    is_admin,
    get_current_user,
)
from api.personas import router as personas_router
from infra import repositories as repo
from infra.state_sync import fusionar_estado_acompaniantes, sincronizar_acompaniantes_en_estado_y_guardar

WEB_ROOT = Path(__file__).resolve().parent.parent / "web"
STATIC_DIR = WEB_ROOT / "static"


# Dependencia para validar que el usuario es administrador
async def get_admin_user(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """Verificar que el usuario es administrador."""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Solo administradores pueden acceder a esto")
    return current_user


# Modelos para autenticación
class LoginRequest(BaseModel):
    """Credenciales de login."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Respuesta de login."""
    access_token: str
    token_type: str
    user_type: str
    username: str


@asynccontextmanager
async def lifespan(_app: FastAPI):
    repo.inicializar_db()
    yield


app = FastAPI(
    title="SofB Train API",
    description="Misma lógica y archivos que la app de escritorio.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(personas_router)


class AsignacionOut(BaseModel):
    conductor: str
    acompanante: str


class ConductorItem(BaseModel):
    """Orden actual en SQLite (misma fila que `conductores` por posición)."""

    id: int
    nombre: str


class EstadoHoyResponse(BaseModel):
    fecha: str
    acompaniantes_orden: list[str]
    no_disponibles_hoy: list[str]
    asignaciones: list[AsignacionOut]
    conductores: list[str]
    conductores_items: list[ConductorItem] = []
    mensaje_turno: str | None = None


class GenerarAsignacionBody(BaseModel):
    """Si se omite, todos los acompañantes del orden cuentan como disponibles."""

    disponibles: list[str] | None = None


class GenerarAsignacionResponse(BaseModel):
    asignaciones: list[AsignacionOut]
    no_disponibles_hoy: list[str]
    mensaje_turno: str | None = None


class CerrarDiaResponse(BaseModel):
    fecha: str
    acompaniantes_orden: list[str]
    mensaje: str
    mensaje_turno: str | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/login", response_model=LoginResponse)
def login(credentials: LoginRequest):
    """Endpoint de login para obtener JWT token."""
    token_data = authenticate_user(credentials.username, credentials.password)
    if not token_data:
        raise HTTPException(status_code=401, detail="Usuario o contraseña inválidos")
    
    access_token = create_access_token(token_data)
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_type=token_data.user_type,
        username=token_data.username,
    )


@app.post("/logout")
def logout():
    """Endpoint de logout (simplemente retorna OK, el cliente elimina el token)."""
    return {"message": "Sesión cerrada"}


@app.get("/me")
def get_current_user_info(current_user: TokenData = Depends(get_current_user)):
    """Obtener información del usuario actual."""
    return {
        "username": current_user.username,
        "user_type": current_user.user_type,
    }


@app.get("/")
def index():
    index_path = WEB_ROOT / "index.html"
    if not index_path.is_file():
        raise HTTPException(status_code=404, detail="UI web no encontrada")
    return FileResponse(index_path)


@app.get("/estado/hoy", response_model=EstadoHoyResponse)
def estado_hoy(response: Response, current_user: TokenData = Depends(get_current_user)):
    response.headers["Cache-Control"] = "no-store, max-age=0, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    estado = sincronizar_acompaniantes_en_estado_y_guardar()

    conductores = repo.cargar_conductores()
    orden = estado.get("acompaniantes_orden", [])
    raw_asig = estado.get("asignaciones_hoy")
    resultados = asignaciones_desde_json(raw_asig if isinstance(raw_asig, list) else None)
    raw_disp = estado.get("disponibles_hoy")
    disp_msg = set(raw_disp) if isinstance(raw_disp, list) else None

    mensaje: str | None = None
    if resultados:
        c, a = resultados[0]
        mensaje = generar_texto_turno(c, a, orden, disponibles=disp_msg)
    elif conductores and orden:
        mensaje = generar_texto_turno(
            conductores[0], orden[0], orden, disponibles=disp_msg
        )

    conductores_items: list[ConductorItem] = []
    if is_admin(current_user):
        filas_cond = repo.listar_personas("conductores")
        conductores_items = [
            ConductorItem(id=pid, nombre=nombre) for pid, nombre in filas_cond
        ]

    return EstadoHoyResponse(
        fecha=estado.get("fecha", ""),
        acompaniantes_orden=orden,
        no_disponibles_hoy=list(estado.get("no_disponibles_hoy", [])),
        asignaciones=[
            AsignacionOut(conductor=c, acompanante=a) for c, a in resultados
        ],
        conductores=conductores,
        conductores_items=conductores_items,
        mensaje_turno=mensaje,
    )


@app.post("/asignacion/generar", response_model=GenerarAsignacionResponse)
def generar_asignacion_endpoint(body: GenerarAsignacionBody, admin_user: TokenData = Depends(get_admin_user)):
    estado = repo.cargar_estado()
    fusionar_estado_acompaniantes(estado)

    conductores = repo.cargar_conductores()
    orden = estado.get("acompaniantes_orden", [])

    if not conductores:
        raise HTTPException(status_code=400, detail="No hay conductores cargados.")
    if not orden:
        raise HTTPException(status_code=400, detail="No hay acompañantes cargados.")

    if body.disponibles is None:
        disponibles = set(orden)
    else:
        disponibles = {str(x).strip() for x in body.disponibles if str(x).strip()}

    asignaciones, no_disp = generar_asignacion(conductores, orden, disponibles)
    estado["no_disponibles_hoy"] = no_disp
    estado["asignaciones_hoy"] = asignaciones_a_json(asignaciones)
    estado["disponibles_hoy"] = [x for x in orden if x in disponibles]
    repo.guardar_estado(estado)

    disp_turno = set(disponibles)
    mensaje_turno: str | None = None
    if asignaciones:
        c0, a0 = asignaciones[0]
        mensaje_turno = generar_texto_turno(c0, a0, orden, disponibles=disp_turno)
    elif conductores and orden:
        mensaje_turno = generar_texto_turno(
            conductores[0], orden[0], orden, disponibles=disp_turno
        )

    return GenerarAsignacionResponse(
        asignaciones=[
            AsignacionOut(conductor=c, acompanante=a) for c, a in asignaciones
        ],
        no_disponibles_hoy=no_disp,
        mensaje_turno=mensaje_turno,
    )


@app.post("/dia/cerrar", response_model=CerrarDiaResponse)
def cerrar_dia(admin_user: TokenData = Depends(get_admin_user)):
    estado = repo.cargar_estado()
    fusionar_estado_acompaniantes(estado)
    conductores = repo.cargar_conductores()
    orden = estado.get("acompaniantes_orden", [])
    raw_asig = estado.get("asignaciones_hoy")
    resultados = asignaciones_desde_json(raw_asig if isinstance(raw_asig, list) else None)

    conductor_hoy, acomp_hoy = resolver_pareja_cierre(
        resultados, conductores, orden
    )

    if conductor_hoy:
        repo.mover_persona_al_final("conductores", conductor_hoy)

    estado = estado_despues_cierre(
        estado,
        conductor_hoy,
        acomp_hoy,
        str(date.today()),
    )
    estado.pop("asignaciones_hoy", None)
    estado.pop("disponibles_hoy", None)
    repo.guardar_estado(estado)

    orden_after = estado.get("acompaniantes_orden", [])
    conductores_after = repo.cargar_conductores()
    mensaje_turno: str | None = None
    if conductores_after and orden_after:
        mensaje_turno = generar_texto_turno(
            conductores_after[0], orden_after[0], orden_after
        )

    return CerrarDiaResponse(
        fecha=estado["fecha"],
        acompaniantes_orden=estado.get("acompaniantes_orden", []),
        mensaje="Día cerrado. Orden de mañana actualizado.",
        mensaje_turno=mensaje_turno,
    )


if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
