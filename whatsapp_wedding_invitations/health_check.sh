#!/bin/bash
#====================================================================
# WhatsApp Wedding Invitations - Health Check Script
# Run after each deployment to verify system health
#====================================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ODOO_PORT=${ODOO_PORT:-8069}
ODOO_HOST=${ODOO_HOST:-localhost}
WHATSAPP_PORT=${WHATSAPP_PORT:-3000}
DOCKER_CONTAINER=${DOCKER_CONTAINER:-whatsapp-bridge}
ODOO_DB=${ODOO_DB:-omevent}
ODOO_CONFIG=${ODOO_CONFIG:-/etc/odoo-server.conf}
ODOO_SERVICE=${ODOO_SERVICE:-odoo-server.service}

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Functions
print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_check() {
    echo -n "  → $1... "
}

print_pass() {
    echo -e "${GREEN}✓ PASS${NC} $1"
    ((PASSED++))
}

print_fail() {
    echo -e "${RED}✗ FAIL${NC} $1"
    ((FAILED++))
}

print_warn() {
    echo -e "${YELLOW}⚠ WARN${NC} $1"
    ((WARNINGS++))
}

print_info() {
    echo -e "  ${BLUE}ℹ${NC} $1"
}

#====================================================================
# 1. ODOO SERVICE CHECKS
#====================================================================
print_header "1. ODOO SERVICE CHECKS"

# Check Odoo service status
print_check "Odoo service status"
if systemctl is-active --quiet $ODOO_SERVICE 2>/dev/null; then
    print_pass ""
else
    print_fail "Service not running"
    echo "    Fix: sudo systemctl start $ODOO_SERVICE"
fi

# Check Odoo process
print_check "Odoo process running"
if pgrep -f "odoo-bin" > /dev/null; then
    PID=$(pgrep -f "odoo-bin" | head -1)
    print_pass "(PID: $PID)"
else
    print_fail "No odoo-bin process found"
fi

# Check Odoo port listening
print_check "Port $ODOO_PORT listening"
if netstat -tlnp 2>/dev/null | grep -q ":$ODOO_PORT " || ss -tlnp 2>/dev/null | grep -q ":$ODOO_PORT "; then
    print_pass ""
else
    print_fail "Port not listening"
fi

# Check Odoo HTTP response
print_check "Odoo HTTP response"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://$ODOO_HOST:$ODOO_PORT/web/login" 2>/dev/null)
if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "303" ]]; then
    print_pass "(HTTP $HTTP_CODE)"
else
    print_fail "(HTTP $HTTP_CODE)"
fi

# Check Odoo config file
print_check "Odoo config file exists"
if [ -f "$ODOO_CONFIG" ]; then
    print_pass "$ODOO_CONFIG"
else
    print_fail "Config not found at $ODOO_CONFIG"
fi

# Check dbfilter setting (IMPORTANT: must be 'dbfilter' not 'db_filter')
print_check "dbfilter configured"
DB_FILTER=$(grep "^dbfilter" "$ODOO_CONFIG" 2>/dev/null | head -1)
if [ -n "$DB_FILTER" ]; then
    print_pass "$DB_FILTER"
else
    # Check for wrong parameter name
    WRONG_FILTER=$(grep "^db_filter" "$ODOO_CONFIG" 2>/dev/null | head -1)
    if [ -n "$WRONG_FILTER" ]; then
        print_fail "Wrong parameter name 'db_filter' - should be 'dbfilter'"
        echo "    Fix: sudo sed -i 's/^db_filter/dbfilter/' $ODOO_CONFIG"
    else
        print_warn "dbfilter not set - webhook will return 404!"
        echo "    Fix: Add 'dbfilter = ^$ODOO_DB\$' to $ODOO_CONFIG"
    fi
fi

#====================================================================
# 2. WHATSAPP SERVER CHECKS
#====================================================================
print_header "2. WHATSAPP SERVER CHECKS"

# Check Docker installed
print_check "Docker installed"
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version 2>/dev/null | cut -d' ' -f3 | tr -d ',')
    print_pass "(v$DOCKER_VERSION)"
else
    print_fail "Docker not installed"
    echo "    Fix: sudo apt install docker.io"
fi

# Check Docker container exists
print_check "WhatsApp container exists"
if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -q "^${DOCKER_CONTAINER}$"; then
    print_pass ""
else
    print_fail "Container '$DOCKER_CONTAINER' not found"
fi

# Check Docker container running
print_check "WhatsApp container running"
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${DOCKER_CONTAINER}$"; then
    UPTIME=$(docker ps --format '{{.Status}}' --filter "name=${DOCKER_CONTAINER}" 2>/dev/null)
    print_pass "($UPTIME)"
else
    print_fail "Container not running"
    echo "    Fix: sudo docker start $DOCKER_CONTAINER"
fi

# Check WhatsApp server port
print_check "WhatsApp server port $WHATSAPP_PORT"
if curl -s "http://localhost:$WHATSAPP_PORT/api/status" > /dev/null 2>&1; then
    print_pass ""
else
    print_warn "Port not responding"
fi

# Check WhatsApp API status
print_check "WhatsApp API status"
WA_STATUS=$(curl -s "http://localhost:$WHATSAPP_PORT/api/status" 2>/dev/null)
if [ -n "$WA_STATUS" ]; then
    IS_READY=$(echo "$WA_STATUS" | grep -o '"ready":[^,}]*' | cut -d':' -f2)
    if [ "$IS_READY" == "true" ]; then
        print_pass "Ready and connected"
    else
        print_warn "Not ready - may need QR scan"
        echo "    Fix: Scan QR code from Odoo WhatsApp Connection"
    fi
else
    print_fail "API not responding"
fi

# Check ODOO_WEBHOOK_URL in container
print_check "ODOO_WEBHOOK_URL configured"
WEBHOOK_URL=$(docker inspect $DOCKER_CONTAINER 2>/dev/null | grep -o 'ODOO_WEBHOOK_URL=[^"]*' | cut -d'=' -f2)
if [ -n "$WEBHOOK_URL" ]; then
    print_pass "$WEBHOOK_URL"
else
    print_warn "ODOO_WEBHOOK_URL not set in container"
fi

# Check container network mode
print_check "Container network mode"
NET_MODE=$(docker inspect $DOCKER_CONTAINER 2>/dev/null | grep -o '"NetworkMode": "[^"]*"' | cut -d'"' -f4)
if [ "$NET_MODE" == "host" ]; then
    print_pass "host (correct)"
else
    print_warn "Not using host network ($NET_MODE)"
    echo "    Recommended: Use --network host for Docker container"
fi

#====================================================================
# 3. WEBHOOK CHECKS
#====================================================================
print_header "3. WEBHOOK ENDPOINT CHECKS"

# Test webhook/test endpoint
print_check "Webhook test endpoint"
TEST_RESPONSE=$(curl -s "http://$ODOO_HOST:$ODOO_PORT/whatsapp/webhook/test" 2>/dev/null)
if echo "$TEST_RESPONSE" | grep -q "ok\|running"; then
    print_pass ""
elif echo "$TEST_RESPONSE" | grep -q "404"; then
    print_fail "404 Not Found - Route not registered"
    echo "    Fix: Ensure db_filter is set and restart Odoo"
else
    print_warn "Unexpected response"
fi

# Test webhook/http endpoint
print_check "Webhook HTTP endpoint"
HTTP_RESPONSE=$(curl -s -X POST "http://$ODOO_HOST:$ODOO_PORT/whatsapp/webhook/http" \
    -H "Content-Type: application/json" \
    -d '{"phoneNumber":"000000000","message":"test","senderName":"HealthCheck"}' 2>/dev/null)
if echo "$HTTP_RESPONSE" | grep -q "success\|error\|result"; then
    print_pass "Endpoint responding"
elif echo "$HTTP_RESPONSE" | grep -q "404"; then
    print_fail "404 Not Found"
else
    print_warn "Unexpected response: ${HTTP_RESPONSE:0:50}"
fi

# Test from inside Docker container
print_check "Webhook from Docker container"
DOCKER_TEST=$(docker exec $DOCKER_CONTAINER curl -s -o /dev/null -w "%{http_code}" "http://localhost:$ODOO_PORT/web/login" 2>/dev/null)
if [[ "$DOCKER_TEST" == "200" || "$DOCKER_TEST" == "303" ]]; then
    print_pass "Docker can reach Odoo (HTTP $DOCKER_TEST)"
else
    print_fail "Docker cannot reach Odoo (HTTP $DOCKER_TEST)"
fi

#====================================================================
# 4. MODULE CHECKS
#====================================================================
print_header "4. MODULE CHECKS"

# Check module directory exists
MODULE_PATH="/odoo/custom/mahara/whatsapp_wedding_invitations"
print_check "Module directory exists"
if [ -d "$MODULE_PATH" ]; then
    print_pass "$MODULE_PATH"
else
    print_warn "Module not found at expected path"
fi

# Check key module files
print_check "Controller file exists"
if [ -f "$MODULE_PATH/controllers/whatsapp_webhook.py" ]; then
    print_pass ""
else
    print_fail "whatsapp_webhook.py not found"
fi

# Check __manifest__.py
print_check "__manifest__.py exists"
if [ -f "$MODULE_PATH/__manifest__.py" ]; then
    VERSION=$(grep -o "'version'.*" "$MODULE_PATH/__manifest__.py" | head -1)
    print_pass "$VERSION"
else
    print_fail "__manifest__.py not found"
fi

# Check addons_path includes module directory
print_check "Module in addons_path"
ADDONS_PATH=$(grep "^addons_path" "$ODOO_CONFIG" 2>/dev/null)
if echo "$ADDONS_PATH" | grep -q "mahara"; then
    print_pass ""
else
    print_warn "Module path may not be in addons_path"
fi

#====================================================================
# 5. NGINX CHECKS (if applicable)
#====================================================================
print_header "5. NGINX CHECKS"

# Check Nginx installed
print_check "Nginx installed"
if command -v nginx &> /dev/null; then
    print_pass ""
else
    print_info "Nginx not installed (optional)"
fi

# Check Nginx running
print_check "Nginx service status"
if systemctl is-active --quiet nginx 2>/dev/null; then
    print_pass ""
else
    print_info "Nginx not running (may be optional)"
fi

# Check Nginx config for webhook
print_check "Nginx webhook location"
if grep -r "whatsapp/webhook" /etc/nginx/ 2>/dev/null | grep -q "X-Odoo-Database"; then
    print_pass "X-Odoo-Database header configured"
else
    print_info "Consider adding X-Odoo-Database header in Nginx"
fi

#====================================================================
# 6. LOG CHECKS
#====================================================================
print_header "6. RECENT LOG ANALYSIS"

# Check for recent errors in Odoo logs
print_check "Recent Odoo errors (last 100 lines)"
ODOO_LOG="/var/log/odoo/odoo-server.log"
if [ -f "$ODOO_LOG" ]; then
    ERROR_COUNT=$(tail -100 "$ODOO_LOG" 2>/dev/null | grep -c "ERROR\|CRITICAL")
    if [ "$ERROR_COUNT" -eq 0 ]; then
        print_pass "No recent errors"
    else
        print_warn "$ERROR_COUNT errors found"
        echo "    Run: tail -100 $ODOO_LOG | grep -i error"
    fi
else
    print_info "Log file not found at $ODOO_LOG"
fi

# Check for webhook activity
print_check "Recent webhook activity"
if [ -f "$ODOO_LOG" ]; then
    WEBHOOK_COUNT=$(tail -500 "$ODOO_LOG" 2>/dev/null | grep -c "webhook")
    if [ "$WEBHOOK_COUNT" -gt 0 ]; then
        print_pass "$WEBHOOK_COUNT webhook entries in recent logs"
    else
        print_info "No recent webhook activity"
    fi
fi

# Check WhatsApp logs for errors
print_check "WhatsApp container errors"
WA_ERRORS=$(docker logs --tail 50 $DOCKER_CONTAINER 2>&1 | grep -c "Error\|error\|failed")
if [ "$WA_ERRORS" -eq 0 ]; then
    print_pass "No recent errors"
else
    print_warn "$WA_ERRORS errors in recent logs"
    echo "    Run: sudo docker logs --tail 50 $DOCKER_CONTAINER"
fi

#====================================================================
# SUMMARY
#====================================================================
print_header "SUMMARY"

TOTAL=$((PASSED + FAILED + WARNINGS))
echo ""
echo -e "  ${GREEN}Passed:${NC}   $PASSED"
echo -e "  ${RED}Failed:${NC}   $FAILED"
echo -e "  ${YELLOW}Warnings:${NC} $WARNINGS"
echo -e "  Total:    $TOTAL checks"
echo ""

if [ $FAILED -eq 0 ]; then
    if [ $WARNINGS -eq 0 ]; then
        echo -e "${GREEN}✓ All checks passed! System is healthy.${NC}"
        exit 0
    else
        echo -e "${YELLOW}⚠ System operational with warnings. Review warnings above.${NC}"
        exit 0
    fi
else
    echo -e "${RED}✗ Some checks failed. Please review and fix issues above.${NC}"
    exit 1
fi

