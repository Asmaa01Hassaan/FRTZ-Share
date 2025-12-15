#!/bin/bash
#====================================================================
# WhatsApp Wedding Invitations - Service Restart Script
# Use this script to safely restart Odoo and WhatsApp services
#====================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration - EDIT THESE FOR YOUR SERVER
ODOO_DB="${ODOO_DB:-omevent}"
ODOO_SERVICE="${ODOO_SERVICE:-odoo-server.service}"
ODOO_CONFIG="${ODOO_CONFIG:-/etc/odoo-server.conf}"
DOCKER_CONTAINER="${DOCKER_CONTAINER:-whatsapp-bridge}"
WHATSAPP_AUTH_PATH="${WHATSAPP_AUTH_PATH:-/odoo/custom/mahara/whatsapp_wedding_invitations/.wwebjs_auth}"
WEBHOOK_URL="http://127.0.0.1:8069/whatsapp/webhook/http"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   WhatsApp Wedding - Service Restart Script    ${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

#====================================================================
# STEP 1: Pre-flight checks
#====================================================================
echo -e "${YELLOW}[1/6] Pre-flight checks...${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (sudo)${NC}"
    exit 1
fi

# Check dbfilter is set correctly
echo -n "  → Checking dbfilter... "
if grep -q "^dbfilter.*=.*${ODOO_DB}" "$ODOO_CONFIG" 2>/dev/null; then
    echo -e "${GREEN}✓ OK${NC}"
else
    echo -e "${YELLOW}⚠ Not set, adding...${NC}"
    
    # Remove any existing db_filter or dbfilter lines
    sed -i '/^db_filter/d' "$ODOO_CONFIG"
    sed -i '/^dbfilter/d' "$ODOO_CONFIG"
    
    # Add correct dbfilter after [options]
    sed -i "/^\[options\]/a dbfilter = ^${ODOO_DB}\$" "$ODOO_CONFIG"
    echo -e "  ${GREEN}✓ Added dbfilter = ^${ODOO_DB}\$${NC}"
fi

#====================================================================
# STEP 2: Stop services
#====================================================================
echo ""
echo -e "${YELLOW}[2/6] Stopping services...${NC}"

echo -n "  → Stopping Odoo... "
systemctl stop "$ODOO_SERVICE" 2>/dev/null || true
sleep 2
echo -e "${GREEN}✓${NC}"

echo -n "  → Stopping WhatsApp container... "
docker stop "$DOCKER_CONTAINER" 2>/dev/null || true
sleep 2
echo -e "${GREEN}✓${NC}"

#====================================================================
# STEP 3: Start Odoo
#====================================================================
echo ""
echo -e "${YELLOW}[3/6] Starting Odoo...${NC}"

systemctl start "$ODOO_SERVICE"
echo "  → Waiting for Odoo to initialize (20 seconds)..."
sleep 20

# Verify Odoo is running
if systemctl is-active --quiet "$ODOO_SERVICE"; then
    echo -e "  ${GREEN}✓ Odoo is running${NC}"
else
    echo -e "  ${RED}✗ Odoo failed to start${NC}"
    journalctl -u "$ODOO_SERVICE" -n 20
    exit 1
fi

# Verify Odoo HTTP response
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8069/web/login" 2>/dev/null)
if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "302" ]]; then
    echo -e "  ${GREEN}✓ Odoo HTTP responding (HTTP $HTTP_CODE)${NC}"
else
    echo -e "  ${YELLOW}⚠ Odoo HTTP returned $HTTP_CODE${NC}"
fi

#====================================================================
# STEP 4: Start WhatsApp container
#====================================================================
echo ""
echo -e "${YELLOW}[4/6] Starting WhatsApp container...${NC}"

# Check if container exists
if docker ps -a --format '{{.Names}}' | grep -q "^${DOCKER_CONTAINER}$"; then
    echo "  → Starting existing container..."
    docker start "$DOCKER_CONTAINER"
else
    echo "  → Creating new container..."
    docker run -d \
        --name "$DOCKER_CONTAINER" \
        --network host \
        --restart unless-stopped \
        -e ODOO_WEBHOOK_URL="$WEBHOOK_URL" \
        -e ODOO_DB_NAME="$ODOO_DB" \
        -v "$WHATSAPP_AUTH_PATH:/app/.wwebjs_auth" \
        whatsapp-bridge
fi

echo "  → Waiting for WhatsApp to initialize (15 seconds)..."
sleep 15

# Verify container is running
if docker ps --format '{{.Names}}' | grep -q "^${DOCKER_CONTAINER}$"; then
    echo -e "  ${GREEN}✓ WhatsApp container is running${NC}"
else
    echo -e "  ${RED}✗ WhatsApp container failed to start${NC}"
    docker logs --tail 20 "$DOCKER_CONTAINER"
    exit 1
fi

#====================================================================
# STEP 5: Verify webhook
#====================================================================
echo ""
echo -e "${YELLOW}[5/6] Verifying webhook...${NC}"

WEBHOOK_RESPONSE=$(curl -s -X POST "http://localhost:8069/whatsapp/webhook/http" \
    -H "Content-Type: application/json" \
    -d '{"phoneNumber":"000000000","message":"test","senderName":"HealthCheck"}' 2>/dev/null)

if echo "$WEBHOOK_RESPONSE" | grep -q "success\|error\|result"; then
    echo -e "  ${GREEN}✓ Webhook is responding${NC}"
    echo "  Response: ${WEBHOOK_RESPONSE:0:80}..."
else
    echo -e "  ${RED}✗ Webhook not responding properly${NC}"
    echo "  Response: $WEBHOOK_RESPONSE"
fi

#====================================================================
# STEP 6: Check WhatsApp connection
#====================================================================
echo ""
echo -e "${YELLOW}[6/6] Checking WhatsApp status...${NC}"

WA_STATUS=$(curl -s "http://localhost:3000/api/status" 2>/dev/null)
if echo "$WA_STATUS" | grep -q '"ready":true'; then
    echo -e "  ${GREEN}✓ WhatsApp is connected and ready${NC}"
else
    echo -e "  ${YELLOW}⚠ WhatsApp needs QR code scan${NC}"
    echo ""
    echo -e "  ${BLUE}Next steps:${NC}"
    echo "  1. Open Odoo in browser"
    echo "  2. Go to: WhatsApp Invitations > WhatsApp Connection"
    echo "  3. Click 'Refresh QR Code'"
    echo "  4. Scan with your phone"
fi

#====================================================================
# Summary
#====================================================================
echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}   Services Restarted Successfully!             ${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "Status:"
echo "  • Odoo:     $(systemctl is-active $ODOO_SERVICE)"
echo "  • WhatsApp: $(docker ps --format '{{.Status}}' --filter name=$DOCKER_CONTAINER)"
echo ""
echo "Useful commands:"
echo "  • Odoo logs:     tail -f /var/log/odoo/odoo-server.log"
echo "  • WhatsApp logs: docker logs -f $DOCKER_CONTAINER"
echo "  • Test webhook:  curl -X POST http://localhost:8069/whatsapp/webhook/http -H 'Content-Type: application/json' -d '{\"phoneNumber\":\"123\",\"message\":\"test\",\"senderName\":\"Test\"}'"

