# Desplegar SofB Train (API + web) en la nube

**Paso a paso en Oracle Cloud (Always Free):** ver [`DEPLOY-OCI.md`](DEPLOY-OCI.md).

---

Este proyecto es una app **FastAPI** que sirve la UI en `/` y la API bajo las mismas rutas que en local. Los datos viven en **SQLite** + **JSON** en el directorio configurado por entorno (por defecto el directorio de trabajo).

## Variables de entorno

| Variable | Descripción |
|----------|-------------|
| `TREN_DATA_DIR` | Carpeta donde se guardan `datos_tren.db` y `estado_tren.json`. Debe ser **persistente** en la nube (volumen). Por defecto: `.` |
| `TREN_DB_PATH` | (Opcional) Ruta completa al `.db` |
| `TREN_STATE_PATH` | (Opcional) Ruta completa al `.json` |

## Local con Docker

```bash
docker compose up --build
```

Abre `http://localhost:8000`. Los datos quedan en el volumen `tren_data`.

## Imagen propia (cualquier VPS / Kubernetes)

```bash
docker build -t tu-registry/sofb-tren:latest .
docker push tu-registry/sofb-tren:latest
```

En el servidor: montá un volumen en `/data` (o el path que uses) y ejecutá con `TREN_DATA_DIR=/data`.

## Plataformas tipo Render / Fly.io / Railway

1. Conectá el repositorio o subí la imagen Docker.
2. **Comando / start**: `python -m uvicorn api.main:app --host 0.0.0.0 --port $PORT`  
   (si la plataforma inyecta `PORT`, mapealo; algunas usan 8000 fijo en la config de UI).
3. Añadí un **disco persistente** o volumen y asigná `TREN_DATA_DIR` a esa ruta. Sin volumen, cada redeploy borra la base.
4. **HTTPS** lo suele dar la plataforma; no hace falta configurarlo en la app.

Si el host inyecta la variable **`PORT`** (p. ej. Render), usá como comando:

`sh -c "python -m uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"`

## Escritorio (`app_tren.py`)

La app Tkinter **no** va dentro de este contenedor: sigue en tu PC o empaquetala aparte (PyInstaller, etc.). El contenedor es solo **web + API**.

## Límites de SQLite en la nube

Un solo archivo SQLite es válido para **pocos usuarios concurrentes** y un solo proceso. Si más adelante necesitás mucha concurrencia, el paso natural es **PostgreSQL** y migrar el estado de JSON a tablas.

## Trabajar “sobre la web ya publicada”

Desde Cursor **no** se puede desplegar automáticamente a tu cuenta sin credenciales y sin que elijas el proveedor. El flujo habitual es:

1. Empaquetar / pushear (Docker o git).
2. En el panel del host (Render, Fly, VPS) redeploy cuando cambies `main`.
3. Opcional: **GitHub Actions** que construya la imagen y la publique en cada tag.

Si querés que el agente **edite código pensando en una URL fija** (CORS, `fetch` absoluto, etc.), pasame la URL pública y el stack (Docker en VPS, Render, etc.) y lo adaptamos en el repo.
