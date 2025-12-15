#!/bin/bash

# Deployment script for WhatsApp Bridge (whatsapp-bridge)
# - Pulls latest code (if repo)
# - Builds Docker image
# - Restarts container with proper environment and volume

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

IMAGE_NAME="whatsapp-bridge"
CONTAINER_NAME="whatsapp-bridge"

# === Optional: pull latest from git if this is a git repo ===
if command -v git >/dev/null 2>&1 && [ -d .git ]; then
  echo "🔄 Pulling latest changes from git..."
  git pull --rebase || echo "⚠️ git pull failed (continuing with local code)"
fi

echo "📦 Building Docker image: $IMAGE_NAME ..."
docker build -t "$IMAGE_NAME" .

echo "🧹 Stopping old container (if exists)..."
if docker ps -a --format '{{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
  docker stop "$CONTAINER_NAME" || true
  docker rm "$CONTAINER_NAME" || true
fi

# === Configure Odoo webhook URL ===
# Adjust this to match your environment.
ODOO_WEBHOOK_URL=${ODOO_WEBHOOK_URL:-"http://localhost:8069/whatsapp/webhook"}

echo "🚀 Starting new container: $CONTAINER_NAME"
echo "   Using ODOO_WEBHOOK_URL=$ODOO_WEBHOOK_URL"

docker run -d \
  --name "$CONTAINER_NAME" \
  --restart unless-stopped \
  -p 3000:3000 \
  -e ODOO_WEBHOOK_URL="$ODOO_WEBHOOK_URL" \
  -v "$PROJECT_DIR/.wwebjs_auth:/app/.wwebjs_auth" \
  "$IMAGE_NAME"

echo "✅ Deployment complete. Current containers:"
docker ps | grep "$CONTAINER_NAME" || echo "⚠️ Container not found in docker ps output. Check logs with: docker logs $CONTAINER_NAME"