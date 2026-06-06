#!/usr/bin/env bash
# ============================================
#  Deploy script - sofb-tren By Di Toro
# ============================================
# Uso:
#   ./deploy.sh           # deploy normal (backup auto si hay DB y no hay backup reciente)
#   ./deploy.sh --backup  # forzar backup antes del deploy

set -e

APP_DIR="/opt/tren/app"
CONTAINER_NAME="sofb-tren"
IMAGE_NAME="sofb-tren:latest"
DATA_DIR="/opt/tren-data"
BACKUP_DIR="/opt/tren-backups"
FORCE_BACKUP=false

for arg in "$@"; do
  case "$arg" in
    --backup) FORCE_BACKUP=true ;;
    *) echo "Opción desconocida: $arg" >&2; exit 1 ;;
  esac
done

needs_backup() {
  if [[ ! -f "${DATA_DIR}/datos_tren.db" ]]; then
    return 1
  fi
  if $FORCE_BACKUP; then
    return 0
  fi
  if [[ ! -d "$BACKUP_DIR" ]]; then
    return 0
  fi
  # Backup reciente (<24h): omitir salvo --backup
  find "$BACKUP_DIR" -maxdepth 1 -name 'tren-data-*.tar.gz' -mtime -1 -print -quit 2>/dev/null | grep -q .
  if [[ $? -eq 0 ]]; then
    return 1
  fi
  return 0
}

run_backup() {
  echo "💾 Creando backup de ${DATA_DIR}..."
  if [[ -x "${APP_DIR}/scripts/backup-data.sh" ]]; then
    TREN_DATA_DIR="$DATA_DIR" BACKUP_DIR="$BACKUP_DIR" "${APP_DIR}/scripts/backup-data.sh"
  elif [[ -x "./scripts/backup-data.sh" ]]; then
    TREN_DATA_DIR="$DATA_DIR" BACKUP_DIR="$BACKUP_DIR" ./scripts/backup-data.sh
  else
    mkdir -p "$BACKUP_DIR"
    ARCHIVE="${BACKUP_DIR}/tren-data-$(date +%Y%m%d-%H%M%S).tar.gz"
    tar -czf "$ARCHIVE" -C "$DATA_DIR" .
    echo "Backup creado: $ARCHIVE"
  fi
}

echo "🚀 Iniciando deploy de $CONTAINER_NAME..."

echo "📁 Entrando a $APP_DIR..."
cd "$APP_DIR"

if needs_backup; then
  run_backup
else
  echo "ℹ️  Backup omitido (sin DB o backup reciente; usá --backup para forzar)."
fi

echo "⬇️  Actualizando código con git pull..."
git pull

echo "🔨 Construyendo imagen Docker..."
docker build -t "$IMAGE_NAME" .

echo "🛑 Eliminando contenedor anterior..."
docker rm -f "$CONTAINER_NAME" 2>/dev/null || echo "   (no había contenedor previo)"

echo "▶️  Levantando nuevo contenedor..."
docker run -d \
  --name "$CONTAINER_NAME" \
  --restart unless-stopped \
  -p 80:8000 \
  -e TREN_DATA_DIR=/data \
  -v "$DATA_DIR":/data \
  "$IMAGE_NAME"

echo ""
echo "✅ Deploy completado exitosamente!"
echo "🌐 La app está corriendo en http://localhost:80"
echo "📋 Revisá logs de migración: docker logs $CONTAINER_NAME 2>&1 | tail -30"
