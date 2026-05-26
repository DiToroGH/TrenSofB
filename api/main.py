"""API REST mínima: mismo estado JSON + SQLite que `app_tren.py`."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.services import (
    asignaciones_a_json,
    asignaciones_desde_json,
    calcular_mensaje_turno_automatico,
    estado_despues_cierre,
    generar_asignacion,
    resolver_mensaje_turno,
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
from infra.state_sync import (
    fusionar_estado_acompaniantes,
    persistir_orden_sqlite_acompaniantes_desde_estado,
    sincronizar_acompaniantes_en_estado_y_guardar,
)

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


class AcompanianteItem(BaseModel):
    """Mismo orden que `acompaniantes_orden` en estado; `id` desde SQLite para mover-extremo."""

    id: int
    nombre: str


class EstadoHoyResponse(BaseModel):
    fecha: str
    acompaniantes_orden: list[str]
    no_disponibles_hoy: list[str]
    asignaciones: list[AsignacionOut]
    conductores: list[str]
    conductores_items: list[ConductorItem] = []
    acompaniantes_items: list[AcompanianteItem] = []
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


class RegistroDiaOut(BaseModel):
    fecha: str
    conductor: str
    acompanante: str | None = None


class PutRegistroDiaBody(BaseModel):
    conductor: str
    acompanante: str | None = None


class MensajeTurnoBody(BaseModel):
    mensaje: str


def _normalizar_fecha_iso(s: str) -> str:
    try:
        datetime.strptime(s, "%Y-%m-%d")
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Fecha inválida (usar YYYY-MM-DD).") from exc
    return s


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
    mensaje = resolver_mensaje_turno(estado, conductores, orden, resultados)

    conductores_items: list[ConductorItem] = []
    acompaniantes_items: list[AcompanianteItem] = []
    if is_admin(current_user):
        filas_cond = repo.listar_personas("conductores")
        conductores_items = [
            ConductorItem(id=pid, nombre=nombre) for pid, nombre in filas_cond
        ]
        filas_acomp = repo.listar_personas("acompaniantes")
        nombre_a_id = {nombre: pid for pid, nombre in filas_acomp}
        vistos: set[str] = set()
        for nombre in orden:
            pid = nombre_a_id.get(nombre)
            if pid is not None:
                acompaniantes_items.append(AcompanianteItem(id=pid, nombre=nombre))
                vistos.add(nombre)
        for pid, nombre in filas_acomp:
            if nombre not in vistos:
                acompaniantes_items.append(AcompanianteItem(id=pid, nombre=nombre))

    return EstadoHoyResponse(
        fecha=estado.get("fecha", ""),
        acompaniantes_orden=orden,
        no_disponibles_hoy=list(estado.get("no_disponibles_hoy", [])),
        asignaciones=[
            AsignacionOut(conductor=c, acompanante=a) for c, a in resultados
        ],
        conductores=conductores,
        conductores_items=conductores_items,
        acompaniantes_items=acompaniantes_items,
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
    disp_turno = set(disponibles)
    mensaje_turno = calcular_mensaje_turno_automatico(
        conductores, orden, asignaciones, disponibles=disp_turno
    )
    if mensaje_turno:
        estado["mensaje_turno"] = mensaje_turno
    else:
        estado.pop("mensaje_turno", None)
    repo.guardar_estado(estado)

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

    fecha_registro_raw = estado.get("fecha") or str(date.today())
    try:
        fecha_registro = date.fromisoformat(str(fecha_registro_raw).strip()[:10]).isoformat()
    except ValueError:
        fecha_registro = str(date.today())

    conductor_hoy, acomp_hoy = resolver_pareja_cierre(
        resultados, conductores, orden
    )

    if conductor_hoy:
        acomp_guardar: str | None = None
        if acomp_hoy and str(acomp_hoy).strip() and str(acomp_hoy) != "SIN ACOMPAÑANTE":
            acomp_guardar = str(acomp_hoy).strip()
        repo.upsert_registro_dia(fecha_registro, str(conductor_hoy).strip(), acomp_guardar)

    if conductor_hoy:
        repo.mover_persona_al_final("conductores", conductor_hoy)

    fecha_estado_raw = str(estado.get("fecha") or str(date.today())).strip()[:10]
    try:
        fecha_estado = date.fromisoformat(fecha_estado_raw)
    except ValueError:
        fecha_estado = date.today()
    fecha_maniana = (fecha_estado + timedelta(days=1)).isoformat()

    estado = estado_despues_cierre(
        estado,
        conductor_hoy,
        acomp_hoy,
        fecha_maniana,
    )
    estado.pop("asignaciones_hoy", None)
    estado.pop("disponibles_hoy", None)
    estado.pop("mensaje_turno", None)
    repo.guardar_estado(estado)
    persistir_orden_sqlite_acompaniantes_desde_estado(estado)

    orden_after = estado.get("acompaniantes_orden", [])
    conductores_after = repo.cargar_conductores()
    mensaje_turno = calcular_mensaje_turno_automatico(
        conductores_after, orden_after, []
    )
    if mensaje_turno:
        estado["mensaje_turno"] = mensaje_turno
        repo.guardar_estado(estado)

    return CerrarDiaResponse(
        fecha=estado["fecha"],
        acompaniantes_orden=estado.get("acompaniantes_orden", []),
        mensaje="Día cerrado. Orden de mañana actualizado.",
        mensaje_turno=mensaje_turno,
    )


@app.put("/estado/mensaje-turno")
def guardar_mensaje_turno(
    body: MensajeTurnoBody,
    admin_user: TokenData = Depends(get_admin_user),
):
    _ = admin_user
    estado = repo.cargar_estado()
    fusionar_estado_acompaniantes(estado)
    texto = str(body.mensaje or "").strip()
    if not texto:
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")
    estado["mensaje_turno"] = texto
    repo.guardar_estado(estado)
    return {"mensaje_turno": texto}


@app.post("/estado/mensaje-turno/regenerar")
def regenerar_mensaje_turno(admin_user: TokenData = Depends(get_admin_user)):
    _ = admin_user
    estado = repo.cargar_estado()
    fusionar_estado_acompaniantes(estado)
    conductores = repo.cargar_conductores()
    orden = estado.get("acompaniantes_orden", [])
    raw_asig = estado.get("asignaciones_hoy")
    resultados = asignaciones_desde_json(raw_asig if isinstance(raw_asig, list) else None)
    raw_disp = estado.get("disponibles_hoy")
    disp_msg = set(raw_disp) if isinstance(raw_disp, list) else None
    mensaje = calcular_mensaje_turno_automatico(
        conductores, orden, resultados, disponibles=disp_msg
    )
    if mensaje:
        estado["mensaje_turno"] = mensaje
    else:
        estado.pop("mensaje_turno", None)
    repo.guardar_estado(estado)
    return {"mensaje_turno": mensaje}


@app.get("/registro/dias", response_model=list[RegistroDiaOut])
def listar_registro_dias(
    desde: str,
    hasta: str,
    current_user: TokenData = Depends(get_current_user),
):
    _ = current_user
    d0 = _normalizar_fecha_iso(desde.strip())
    d1 = _normalizar_fecha_iso(hasta.strip())
    if d0 > d1:
        raise HTTPException(status_code=400, detail="'desde' no puede ser posterior a 'hasta'.")
    limite_retencion = (date.today() - timedelta(days=122)).isoformat()
    repo.purgar_registro_antes_de(limite_retencion)
    rows = repo.list_registro_dias_entre(d0, d1)
    return [
        RegistroDiaOut(fecha=f, conductor=c, acompanante=a) for f, c, a in rows
    ]


@app.put("/registro/dia/{fecha}", response_model=RegistroDiaOut)
def actualizar_registro_dia_pasado(
    fecha: str,
    body: PutRegistroDiaBody,
    admin_user: TokenData = Depends(get_admin_user),
):
    _ = admin_user
    f = _normalizar_fecha_iso(fecha.strip())
    if date.fromisoformat(f) >= date.today():
        raise HTTPException(
            status_code=400,
            detail="Solo se pueden editar días ya finalizados (anteriores a hoy).",
        )
    conductor = str(body.conductor or "").strip()
    if not conductor:
        raise HTTPException(status_code=400, detail="Conductor requerido.")
    conductores_ok = set(repo.cargar_conductores())
    if conductor not in conductores_ok:
        raise HTTPException(
            status_code=400,
            detail="El conductor debe existir en la lista actual.",
        )
    acomp: str | None = None
    if body.acompanante is not None and str(body.acompanante).strip():
        acomp = str(body.acompanante).strip()
        acomps_ok = set(repo.cargar_acompaniantes())
        if acomp not in acomps_ok:
            raise HTTPException(
                status_code=400,
                detail="El acompañante debe existir en la lista actual.",
            )
    repo.upsert_registro_dia(f, conductor, acomp)
    return RegistroDiaOut(fecha=f, conductor=conductor, acompanante=acomp)


if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
