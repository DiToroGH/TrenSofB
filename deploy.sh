# ============================================
#  Deploy script - sofb-tren By Di Toro

# ============================================

set -e  # Detiene el script si cualquier comando falla

APP_DIR="/opt/tren/app"
CONTAINER_NAME="sofb-tren"
IMAGE_NAME="sofb-tren:latest"
DATA_DIR="/opt/tren-data"

echo "🚀 Iniciando deploy de $CONTAINER_NAME..."

# 1. Ir al directorio de la app
echo "📁 Entrando a $APP_DIR..."
cd "$APP_DIR"

# 2. Actualizar código
echo "⬇️  Actualizando código con git pull..."
git pull

# 3. Build de la imagen
echo "🔨 Construyendo imagen Docker..."
docker build -t "$IMAGE_NAME" .

# 4. Detener y eliminar contenedor anterior
echo "🛑 Eliminando contenedor anterior..."
docker rm -f "$CONTAINER_NAME" 2>/dev/null || echo "   (no había contenedor previo)"

# 5. Levantar nuevo contenedor
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
