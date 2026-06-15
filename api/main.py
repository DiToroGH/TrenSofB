"""API REST mínima: mismo estado JSON + SQLite que `app_tren.py`."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.services import (
    asignaciones_a_json,
    asignaciones_desde_json,
    calcular_mensaje_turno_automatico,
    conductor_rota_al_cerrar,
    estado_despues_cierre,
    generar_asignacion,
    normalizar_fijos_semana,
    orden_conductores_para_dia,
    resolver_mensaje_turno,
    resolver_pareja_cierre,
    sanitizar_segundo_acompaniante_estado,
)
from core.auth import (
    authenticate_user,
    create_access_token,
    verify_token,
    TokenData,
    is_admin,
    get_current_user,
)
from api.deps import get_linea_id_for_user
from api.lineas import router as lineas_router
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
    logging.basicConfig(level=logging.INFO)
    repo.inicializar_db()
    yield


app = FastAPI(
    title="Train Schedule API",
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


@app.middleware("http")
async def no_cache_ui_assets(request: Request, call_next):
    """Evita JS/CSS/HTML obsoletos tras despliegues (p. ej. VM OCI)."""
    response = await call_next(request)
    path = request.url.path
    if path == "/" or (
        path.startswith("/static/")
        and path.rsplit(".", 1)[-1].lower() in ("js", "css", "html")
    ):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
    return response


app.include_router(personas_router)
app.include_router(lineas_router)


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
    segundo_acompanante: str | None = None
    linea_id: int = 1
    linea_nombre: str = "SofB"
    conductores_fijos_semana: dict[str, str | None] = {}


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
    segundo_acompanante: str | None = None


class PutRegistroDiaBody(BaseModel):
    conductor: str
    acompanante: str | None = None


class MensajeTurnoBody(BaseModel):
    mensaje: str


class SegundoAcompanianteBody(BaseModel):
    nombre: str | None = None


class ConductoresFijosBody(BaseModel):
    """0=lunes … 6=domingo (`date.weekday()`). `conductor` null o vacío quita el fijo."""
    dia_semana: int
    conductor: str | None = None


def _weekday_desde_fecha_iso(fecha: str) -> int:
    try:
        return date.fromisoformat(str(fecha).strip()[:10]).weekday()
    except ValueError:
        return date.today().weekday()


def _fijos_semana_desde_estado(estado: dict) -> dict[int, str]:
    return normalizar_fijos_semana(estado.get("conductores_fijos_semana"))


def _conductores_fijos_api(estado: dict) -> dict[str, str | None]:
    fijos = _fijos_semana_desde_estado(estado)
    return {str(d): fijos[d] for d in sorted(fijos)}


def _normalizar_fecha_iso(s: str) -> str:
    try:
        datetime.strptime(s, "%Y-%m-%d")
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Fecha inválida (usar YYYY-MM-DD).") from exc
    return s


def _personas_linea(linea_id: int) -> set[str]:
    return set(repo.cargar_conductores(linea_id)) | set(
        repo.cargar_acompaniantes(linea_id)
    )


def _fecha_editable_en_registro(f: str, linea_id: int) -> bool:
    """Pasado: siempre. Hoy: si hay registro guardado o asignación confirmada en estado."""
    f_date = date.fromisoformat(f)
    hoy = date.today()
    if f_date > hoy:
        return False
    if f_date < hoy:
        return True
    if repo.registro_dia_existe(f, linea_id):
        return True
    estado = repo.cargar_estado(linea_id)
    fecha_estado = str(estado.get("fecha") or "").strip()[:10]
    if fecha_estado != f:
        return False
    raw_asig = estado.get("asignaciones_hoy")
    resultados = asignaciones_desde_json(raw_asig if isinstance(raw_asig, list) else None)
    return bool(resultados)


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
    return FileResponse(
        index_path,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
        },
    )


@app.get("/estado/hoy", response_model=EstadoHoyResponse)
def estado_hoy(
    response: Response,
    current_user: TokenData = Depends(get_current_user),
    linea_id: int = Depends(get_linea_id_for_user),
):
    response.headers["Cache-Control"] = "no-store, max-age=0, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    estado = sincronizar_acompaniantes_en_estado_y_guardar(linea_id)

    conductores = repo.cargar_conductores(linea_id)
    orden = estado.get("acompaniantes_orden", [])
    raw_asig = estado.get("asignaciones_hoy")
    resultados = asignaciones_desde_json(raw_asig if isinstance(raw_asig, list) else None)
    mensaje = resolver_mensaje_turno(estado, conductores, orden, resultados)

    conductores_items: list[ConductorItem] = []
    acompaniantes_items: list[AcompanianteItem] = []
    linea_info = repo.obtener_linea(linea_id)
    linea_nombre = linea_info[1] if linea_info else "SofB"

    if is_admin(current_user):
        filas_cond = repo.listar_personas("conductores", linea_id)
        conductores_items = [
            ConductorItem(id=pid, nombre=nombre) for pid, nombre in filas_cond
        ]
        filas_acomp = repo.listar_personas("acompaniantes", linea_id)
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
        segundo_acompanante=_segundo_acompanante_desde_estado(estado),
        linea_id=linea_id,
        linea_nombre=linea_nombre,
        conductores_fijos_semana=_conductores_fijos_api(estado),
    )


def _segundo_acompanante_desde_estado(estado: dict) -> str | None:
    raw = estado.get("segundo_acompanante_hoy")
    if raw is None:
        return None
    s = str(raw).strip()
    return s if s else None


def _validar_segundo_acompaniante(
    nombre: str | None,
    orden: list[str],
    vip: str | None,
) -> str | None:
    if nombre is None or not str(nombre).strip():
        return None
    elegido = str(nombre).strip()
    if elegido not in orden:
        raise HTTPException(
            status_code=400,
            detail="El segundo acompañante debe estar en el orden actual.",
        )
    if vip and elegido == vip:
        raise HTTPException(
            status_code=400,
            detail="El segundo acompañante no puede ser el mismo VIP del turno.",
        )
    return elegido


@app.post("/asignacion/generar", response_model=GenerarAsignacionResponse)
def generar_asignacion_endpoint(
    body: GenerarAsignacionBody,
    admin_user: TokenData = Depends(get_admin_user),
    linea_id: int = Depends(get_linea_id_for_user),
):
    _ = admin_user
    estado = repo.cargar_estado(linea_id)
    fusionar_estado_acompaniantes(estado, linea_id)

    conductores = repo.cargar_conductores(linea_id)
    orden = estado.get("acompaniantes_orden", [])

    if not conductores:
        raise HTTPException(status_code=400, detail="No hay conductores cargados.")
    if not orden:
        raise HTTPException(status_code=400, detail="No hay acompañantes cargados.")

    if body.disponibles is None:
        disponibles = set(orden)
    else:
        disponibles = {str(x).strip() for x in body.disponibles if str(x).strip()}

    fijos = _fijos_semana_desde_estado(estado)
    weekday = _weekday_desde_fecha_iso(str(estado.get("fecha") or date.today()))
    cond_orden = orden_conductores_para_dia(conductores, fijos, weekday)
    if not cond_orden:
        raise HTTPException(
            status_code=400,
            detail="No hay conductores activos para este día de la semana.",
        )

    asignaciones, no_disp = generar_asignacion(cond_orden, orden, disponibles)
    estado["no_disponibles_hoy"] = no_disp
    estado["asignaciones_hoy"] = asignaciones_a_json(asignaciones)
    estado["disponibles_hoy"] = [x for x in orden if x in disponibles]
    vip_nuevo = asignaciones[0][1] if asignaciones else None
    sanitizar_segundo_acompaniante_estado(estado, vip_nuevo, orden)
    disp_turno = set(disponibles)
    mensaje_turno = calcular_mensaje_turno_automatico(
        cond_orden, orden, asignaciones, disponibles=disp_turno
    )
    if mensaje_turno:
        estado["mensaje_turno"] = mensaje_turno
    else:
        estado.pop("mensaje_turno", None)
    repo.guardar_estado(estado, linea_id)

    return GenerarAsignacionResponse(
        asignaciones=[
            AsignacionOut(conductor=c, acompanante=a) for c, a in asignaciones
        ],
        no_disponibles_hoy=no_disp,
        mensaje_turno=mensaje_turno,
    )


@app.post("/dia/cerrar", response_model=CerrarDiaResponse)
def cerrar_dia(
    admin_user: TokenData = Depends(get_admin_user),
    linea_id: int = Depends(get_linea_id_for_user),
):
    _ = admin_user
    estado = repo.cargar_estado(linea_id)
    fusionar_estado_acompaniantes(estado, linea_id)
    conductores = repo.cargar_conductores(linea_id)
    orden = estado.get("acompaniantes_orden", [])
    raw_asig = estado.get("asignaciones_hoy")
    resultados = asignaciones_desde_json(raw_asig if isinstance(raw_asig, list) else None)

    fijos = _fijos_semana_desde_estado(estado)
    fecha_registro_raw = estado.get("fecha") or str(date.today())
    try:
        fecha_registro = date.fromisoformat(str(fecha_registro_raw).strip()[:10]).isoformat()
        weekday_cierre = date.fromisoformat(fecha_registro).weekday()
    except ValueError:
        fecha_registro = str(date.today())
        weekday_cierre = date.today().weekday()

    conductor_hoy, acomp_hoy = resolver_pareja_cierre(
        resultados,
        conductores,
        orden,
        weekday=weekday_cierre,
        fijos_semana=fijos,
    )

    segundo_hoy = _segundo_acompanante_desde_estado(estado)

    if conductor_hoy:
        acomp_guardar: str | None = None
        if acomp_hoy and str(acomp_hoy).strip() and str(acomp_hoy) != "SIN ACOMPAÑANTE":
            acomp_guardar = str(acomp_hoy).strip()
        repo.upsert_registro_dia(
            fecha_registro,
            str(conductor_hoy).strip(),
            acomp_guardar,
            linea_id,
            segundo_acompanante=segundo_hoy,
        )

    if conductor_hoy and conductor_rota_al_cerrar(conductor_hoy, fijos, weekday_cierre):
        repo.mover_persona_al_final("conductores", conductor_hoy, linea_id)

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
        segundo_acompanante_hoy=segundo_hoy,
    )
    estado.pop("asignaciones_hoy", None)
    estado.pop("disponibles_hoy", None)
    estado.pop("mensaje_turno", None)
    repo.guardar_estado(estado, linea_id)
    persistir_orden_sqlite_acompaniantes_desde_estado(estado, linea_id)

    orden_after = estado.get("acompaniantes_orden", [])
    conductores_after = repo.cargar_conductores(linea_id)
    mensaje_turno = calcular_mensaje_turno_automatico(
        conductores_after, orden_after, []
    )
    if mensaje_turno:
        estado["mensaje_turno"] = mensaje_turno
        repo.guardar_estado(estado, linea_id)

    return CerrarDiaResponse(
        fecha=estado["fecha"],
        acompaniantes_orden=estado.get("acompaniantes_orden", []),
        mensaje="Día cerrado. Orden de mañana actualizado.",
        mensaje_turno=mensaje_turno,
    )


@app.put("/estado/conductores-fijos-semana")
def guardar_conductor_fijo_semana(
    body: ConductoresFijosBody,
    admin_user: TokenData = Depends(get_admin_user),
    linea_id: int = Depends(get_linea_id_for_user),
):
    _ = admin_user
    if body.dia_semana < 0 or body.dia_semana > 6:
        raise HTTPException(status_code=400, detail="dia_semana debe ser 0–6 (lunes–domingo).")
    estado = repo.cargar_estado(linea_id)
    conductores = set(repo.cargar_conductores(linea_id))
    fijos = dict(estado.get("conductores_fijos_semana") or {})
    clave = str(body.dia_semana)
    nombre = str(body.conductor or "").strip()
    if nombre:
        if nombre not in conductores:
            raise HTTPException(
                status_code=400,
                detail="El conductor debe existir en la lista actual.",
            )
        fijos[clave] = nombre
    else:
        fijos.pop(clave, None)
    if fijos:
        estado["conductores_fijos_semana"] = fijos
    else:
        estado.pop("conductores_fijos_semana", None)
    repo.guardar_estado(estado, linea_id)
    return {"conductores_fijos_semana": _conductores_fijos_api(estado)}


@app.put("/estado/segundo-acompanante")
def guardar_segundo_acompaniante(
    body: SegundoAcompanianteBody,
    admin_user: TokenData = Depends(get_admin_user),
    linea_id: int = Depends(get_linea_id_for_user),
):
    _ = admin_user
    estado = repo.cargar_estado(linea_id)
    fusionar_estado_acompaniantes(estado, linea_id)
    orden = estado.get("acompaniantes_orden", [])
    raw_asig = estado.get("asignaciones_hoy")
    resultados = asignaciones_desde_json(raw_asig if isinstance(raw_asig, list) else None)
    vip = resultados[0][1] if resultados else (orden[0] if orden else None)
    elegido = _validar_segundo_acompaniante(body.nombre, orden, vip)
    if elegido:
        estado["segundo_acompanante_hoy"] = elegido
    else:
        estado.pop("segundo_acompanante_hoy", None)
    repo.guardar_estado(estado, linea_id)
    return {"segundo_acompanante": elegido}


@app.put("/estado/mensaje-turno")
def guardar_mensaje_turno(
    body: MensajeTurnoBody,
    admin_user: TokenData = Depends(get_admin_user),
    linea_id: int = Depends(get_linea_id_for_user),
):
    _ = admin_user
    estado = repo.cargar_estado(linea_id)
    fusionar_estado_acompaniantes(estado, linea_id)
    texto = str(body.mensaje or "").strip()
    if not texto:
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")
    estado["mensaje_turno"] = texto
    repo.guardar_estado(estado, linea_id)
    return {"mensaje_turno": texto}


@app.post("/estado/mensaje-turno/regenerar")
def regenerar_mensaje_turno(
    admin_user: TokenData = Depends(get_admin_user),
    linea_id: int = Depends(get_linea_id_for_user),
):
    _ = admin_user
    estado = repo.cargar_estado(linea_id)
    fusionar_estado_acompaniantes(estado, linea_id)
    conductores = repo.cargar_conductores(linea_id)
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
    repo.guardar_estado(estado, linea_id)
    return {"mensaje_turno": mensaje}


@app.get("/registro/dias", response_model=list[RegistroDiaOut])
def listar_registro_dias(
    desde: str,
    hasta: str,
    current_user: TokenData = Depends(get_current_user),
    linea_id: int = Depends(get_linea_id_for_user),
):
    _ = current_user
    d0 = _normalizar_fecha_iso(desde.strip())
    d1 = _normalizar_fecha_iso(hasta.strip())
    if d0 > d1:
        raise HTTPException(status_code=400, detail="'desde' no puede ser posterior a 'hasta'.")
    limite_retencion = (date.today() - timedelta(days=122)).isoformat()
    repo.purgar_registro_antes_de(limite_retencion, linea_id)
    rows = repo.list_registro_dias_entre(d0, d1, linea_id)
    return [
        RegistroDiaOut(fecha=f, conductor=c, acompanante=a, segundo_acompanante=s)
        for f, c, a, s in rows
    ]


@app.put("/registro/dia/{fecha}", response_model=RegistroDiaOut)
def actualizar_registro_dia_pasado(
    fecha: str,
    body: PutRegistroDiaBody,
    admin_user: TokenData = Depends(get_admin_user),
    linea_id: int = Depends(get_linea_id_for_user),
):
    _ = admin_user
    f = _normalizar_fecha_iso(fecha.strip())
    if not _fecha_editable_en_registro(f, linea_id):
        raise HTTPException(
            status_code=400,
            detail="Hoy solo se puede editar si el día ya está confirmado (registro o asignación generada).",
        )
    conductor = str(body.conductor or "").strip()
    if not conductor:
        raise HTTPException(status_code=400, detail="Conductor requerido.")
    personas_ok = _personas_linea(linea_id)
    if conductor not in personas_ok:
        raise HTTPException(
            status_code=400,
            detail="La persona debe existir en la lista actual (conductores o acompañantes).",
        )
    acomp: str | None = None
    if body.acompanante is not None and str(body.acompanante).strip():
        acomp = str(body.acompanante).strip()
        acomps_ok = set(repo.cargar_acompaniantes(linea_id))
        if acomp not in acomps_ok:
            raise HTTPException(
                status_code=400,
                detail="El acompañante debe existir en la lista actual.",
            )
    repo.upsert_registro_dia(f, conductor, acomp, linea_id)
    return RegistroDiaOut(fecha=f, conductor=conductor, acompanante=acomp)


if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
