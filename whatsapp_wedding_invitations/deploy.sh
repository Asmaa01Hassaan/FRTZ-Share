#!/bin/bash
#====================================================================
# WhatsApp Wedding Invitations - Deployment Script
# Use this script to deploy/update the module on production server
#====================================================================

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration - EDIT THESE FOR YOUR SERVER
ODOO_DB=${ODOO_DB:-omevent}
ODOO_SERVICE=${ODOO_SERVICE:-odoo-server.service}
ODOO_CONFIG=${ODOO_CONFIG:-/etc/odoo-server.conf}
ODOO_USER=${ODOO_USER:-odoo}
MODULE_NAME="whatsapp_wedding_invitations"
MODULE_SOURCE="/odoo/custom/mahara/$MODULE_NAME"
DOCKER_CONTAINER="whatsapp-bridge"
WHATSAPP_AUTH_PATH="$MODULE_SOURCE/.wwebjs_auth"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}WhatsApp Wedding Invitations Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --full          Full deployment (module + docker rebuild)"
    echo "  --module        Update module only (restart Odoo)"
    echo "  --docker        Rebuild Docker container only"
    echo "  --restart       Restart services only"
    echo "  --check         Run health check only"
    echo "  --help          Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 --full       # Full deployment after code changes"
    echo "  $0 --module     # Quick update after Python changes"
    echo "  $0 --restart    # Just restart services"
}

# Parse arguments
ACTION=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --full)
            ACTION="full"
            shift
            ;;
        --module)
            ACTION="module"
            shift
            ;;
        --docker)
            ACTION="docker"
            shift
            ;;
        --restart)
            ACTION="restart"
            shift
            ;;
        --check)
            ACTION="check"
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_usage
            exit 1
            ;;
    esac
done

if [ -z "$ACTION" ]; then
    show_usage
    exit 1
fi

#====================================================================
# FUNCTIONS
#====================================================================

stop_odoo() {
    echo -e "${YELLOW}→ Stopping Odoo...${NC}"
    sudo systemctl stop $ODOO_SERVICE || true
    sleep 3
    echo -e "${GREEN}  ✓ Odoo stopped${NC}"
}

start_odoo() {
    echo -e "${YELLOW}→ Starting Odoo...${NC}"
    sudo systemctl start $ODOO_SERVICE
    sleep 10
    if systemctl is-active --quiet $ODOO_SERVICE; then
        echo -e "${GREEN}  ✓ Odoo started${NC}"
    else
        echo -e "${RED}  ✗ Odoo failed to start${NC}"
        sudo journalctl -u $ODOO_SERVICE -n 20
        exit 1
    fi
}

upgrade_module() {
    echo -e "${YELLOW}→ Upgrading module $MODULE_NAME...${NC}"
    sudo -u $ODOO_USER /odoo/odoo-server/odoo-bin \
        -c $ODOO_CONFIG \
        -d $ODOO_DB \
        -u $MODULE_NAME \
        --stop-after-init
    echo -e "${GREEN}  ✓ Module upgraded${NC}"
}

restart_docker() {
    echo -e "${YELLOW}→ Restarting WhatsApp Docker container...${NC}"
    sudo docker restart $DOCKER_CONTAINER || {
        echo -e "${RED}  ✗ Container not found, trying to start...${NC}"
        sudo docker start $DOCKER_CONTAINER || {
            echo -e "${RED}  ✗ Could not start container${NC}"
            return 1
        }
    }
    sleep 10
    echo -e "${GREEN}  ✓ WhatsApp container restarted${NC}"
}

rebuild_docker() {
    echo -e "${YELLOW}→ Rebuilding WhatsApp Docker image...${NC}"
    
    # Stop existing container
    sudo docker stop $DOCKER_CONTAINER 2>/dev/null || true
    sudo docker rm $DOCKER_CONTAINER 2>/dev/null || true
    
    # Build new image
    cd $MODULE_SOURCE
    sudo docker build -t whatsapp-bridge .
    
    # Start new container
    echo -e "${YELLOW}→ Starting new container...${NC}"
    sudo docker run -d \
        --name $DOCKER_CONTAINER \
        --network host \
        --restart unless-stopped \
        -e ODOO_WEBHOOK_URL=http://127.0.0.1:8069/whatsapp/webhook/http \
        -e ODOO_DB_NAME=$ODOO_DB \
        -v $WHATSAPP_AUTH_PATH:/app/.wwebjs_auth \
        whatsapp-bridge
    
    sleep 15
    echo -e "${GREEN}  ✓ WhatsApp container rebuilt and started${NC}"
}

run_health_check() {
    echo -e "${YELLOW}→ Running health check...${NC}"
    if [ -f "$MODULE_SOURCE/health_check.sh" ]; then
        bash "$MODULE_SOURCE/health_check.sh"
    else
        echo -e "${RED}  ✗ health_check.sh not found${NC}"
    fi
}

check_db_filter() {
    echo -e "${YELLOW}→ Checking db_filter...${NC}"
    if grep -q "^db_filter" $ODOO_CONFIG; then
        echo -e "${GREEN}  ✓ db_filter is set${NC}"
    else
        echo -e "${YELLOW}  ⚠ Adding db_filter to config...${NC}"
        sudo sed -i "/^\[options\]/a db_filter = ^$ODOO_DB\$" $ODOO_CONFIG
        echo -e "${GREEN}  ✓ db_filter added${NC}"
    fi
}

#====================================================================
# MAIN EXECUTION
#====================================================================

case $ACTION in
    full)
        echo -e "${BLUE}Starting FULL deployment...${NC}"
        echo ""
        check_db_filter
        stop_odoo
        upgrade_module
        rebuild_docker
        start_odoo
        sleep 5
        run_health_check
        ;;
    
    module)
        echo -e "${BLUE}Starting MODULE update...${NC}"
        echo ""
        stop_odoo
        upgrade_module
        start_odoo
        sleep 5
        run_health_check
        ;;
    
    docker)
        echo -e "${BLUE}Starting DOCKER rebuild...${NC}"
        echo ""
        rebuild_docker
        run_health_check
        ;;
    
    restart)
        echo -e "${BLUE}Restarting services...${NC}"
        echo ""
        stop_odoo
        start_odoo
        restart_docker
        run_health_check
        ;;
    
    check)
        run_health_check
        ;;
esac

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "  1. If WhatsApp shows QR code, scan it from Odoo interface"
echo "  2. Test sending a message from WhatsApp"
echo "  3. Check logs: tail -f /var/log/odoo/odoo-server.log | grep whatsapp"

