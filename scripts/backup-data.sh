#!/usr/bin/env bash
# Backup de datos persistentes SofB Train (SQLite + estado JSON).
# Uso: ./scripts/backup-data.sh
#      TREN_DATA_DIR=/opt/tren-data BACKUP_DIR=/opt/tren-backups ./scripts/backup-data.sh

set -euo pipefail

DATA_DIR="${TREN_DATA_DIR:-/opt/tren-data}"
BACKUP_DIR="${BACKUP_DIR:-/opt/tren-backups}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
ARCHIVE_NAME="tren-data-${TIMESTAMP}.tar.gz"

if [[ ! -d "$DATA_DIR" ]]; then
  echo "ERROR: directorio de datos no existe: $DATA_DIR" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"

# Empaquetar el contenido del directorio de datos (no el path padre completo).
tar -czf "${BACKUP_DIR}/${ARCHIVE_NAME}" -C "$DATA_DIR" .

echo "Backup creado: ${BACKUP_DIR}/${ARCHIVE_NAME}"
ls -lh "${BACKUP_DIR}/${ARCHIVE_NAME}"
