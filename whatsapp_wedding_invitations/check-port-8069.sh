#!/bin/bash
# Script to check if Port 8069 is open and accessible
# Usage: ./check-port-8069.sh

echo "=========================================="
echo "Checking Port 8069 Status"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check 1: Is Odoo service running?
echo "1. Checking if Odoo service is running..."

# Check systemd service status
ODOO_SERVICE_NAME="odoo-server.service"
if systemctl is-active --quiet "$ODOO_SERVICE_NAME" 2>/dev/null; then
    echo -e "${GREEN}✅ Odoo service ($ODOO_SERVICE_NAME) is active${NC}"
    SERVICE_STATUS=$(systemctl is-active "$ODOO_SERVICE_NAME" 2>/dev/null)
    echo "   Service status: $SERVICE_STATUS"
    
    # Show service status summary
    if systemctl is-enabled --quiet "$ODOO_SERVICE_NAME" 2>/dev/null; then
        echo -e "${GREEN}   ✅ Service is enabled (starts on boot)${NC}"
    else
        echo -e "${YELLOW}   ⚠️  Service is not enabled (won't start on boot)${NC}"
    fi
elif systemctl list-unit-files | grep -q "$ODOO_SERVICE_NAME"; then
    echo -e "${RED}❌ Odoo service ($ODOO_SERVICE_NAME) exists but is not active${NC}"
    echo "   To start: sudo systemctl start $ODOO_SERVICE_NAME"
else
    echo -e "${YELLOW}⚠️  Odoo service ($ODOO_SERVICE_NAME) not found${NC}"
    echo "   Checking for process instead..."
fi

# Also check if process is running
if pgrep -f "odoo-bin" > /dev/null; then
    echo -e "${GREEN}✅ Odoo process is running${NC}"
    ODOO_PROCESS=$(ps aux | grep odoo-bin | grep -v grep | head -1)
    echo "   Process: $ODOO_PROCESS"
    
    # Extract config file from process (multiple methods for compatibility)
    ODOO_CONF_FROM_PROCESS=""
    # Method 1: Using grep -oP (if available)
    if echo "$ODOO_PROCESS" | grep -oP '\-c\s+\K[^\s]+' > /dev/null 2>&1; then
        ODOO_CONF_FROM_PROCESS=$(echo "$ODOO_PROCESS" | grep -oP '\-c\s+\K[^\s]+' | head -1)
    # Method 2: Using sed (more compatible)
    elif echo "$ODOO_PROCESS" | grep -q '\-c'; then
        ODOO_CONF_FROM_PROCESS=$(echo "$ODOO_PROCESS" | sed -n 's/.*-c[[:space:]]*\([^[:space:]]*\).*/\1/p' | head -1)
    # Method 3: Using awk
    else
        ODOO_CONF_FROM_PROCESS=$(echo "$ODOO_PROCESS" | awk '{for(i=1;i<NF;i++) if($i=="-c") print $(i+1)}' | head -1)
    fi
    
    if [ -n "$ODOO_CONF_FROM_PROCESS" ]; then
        echo -e "${GREEN}   📄 Config file: $ODOO_CONF_FROM_PROCESS${NC}"
        if [ -f "$ODOO_CONF_FROM_PROCESS" ]; then
            echo -e "${GREEN}   ✅ Config file exists${NC}"
        else
            echo -e "${RED}   ❌ Config file not found at this path${NC}"
        fi
    fi
else
    if ! systemctl is-active --quiet "$ODOO_SERVICE_NAME" 2>/dev/null; then
        echo -e "${RED}❌ Odoo process is NOT running${NC}"
        echo "   To start: sudo systemctl start $ODOO_SERVICE_NAME"
    fi
fi
echo ""

# Check 1.5: Odoo configuration file
echo "1.5. Checking Odoo configuration..."

# Try to find config file from running process
RUNNING_CONF=$(ps aux | grep odoo-bin | grep -v grep | grep -oP '\-c\s+\K[^\s]+' | head -1)
if [ -n "$RUNNING_CONF" ] && [ -f "$RUNNING_CONF" ]; then
    echo -e "${GREEN}   ✅ Found config from running process: $RUNNING_CONF${NC}"
fi

# Priority order: running process config, then common locations
ODOO_CONF_FILES=(
    "$RUNNING_CONF"
    "/etc/odoo-server.conf"      # Your server's config path
    "/etc/odoo/odoo.conf"
    "/odoo/odoo.conf"
    "/odoo/odoo-server.conf"
    "$(pwd)/odoo.conf"
    "$HOME/odoo.conf"
)
ODOO_CONF_FOUND=false

for conf_file in "${ODOO_CONF_FILES[@]}"; do
    if [ -f "$conf_file" ]; then
        echo -e "${GREEN}   ✅ Found config: $conf_file${NC}"
        ODOO_CONF_FOUND=true
        
        # Check http_port
        HTTP_PORT=$(grep "^http_port" "$conf_file" 2>/dev/null | head -1 | awk -F'=' '{print $2}' | tr -d ' ')
        if [ -n "$HTTP_PORT" ]; then
            echo "   HTTP Port: $HTTP_PORT"
        fi
        
        # Check http_interface
        HTTP_INTERFACE=$(grep "^http_interface" "$conf_file" 2>/dev/null | head -1 | awk -F'=' '{print $2}' | tr -d ' ')
        if [ -z "$HTTP_INTERFACE" ] || [ "$HTTP_INTERFACE" == "" ]; then
            echo -e "${GREEN}   ✅ http_interface is empty (listening on all interfaces 0.0.0.0)${NC}"
        elif [ "$HTTP_INTERFACE" == "0.0.0.0" ]; then
            echo -e "${GREEN}   ✅ http_interface = 0.0.0.0 (accessible from outside)${NC}"
        elif [ "$HTTP_INTERFACE" == "127.0.0.1" ]; then
            echo -e "${YELLOW}   ⚠️  http_interface = 127.0.0.1 (localhost only)${NC}"
            echo -e "${GREEN}   ✅ This is secure when using Nginx reverse proxy${NC}"
        else
            echo "   http_interface = $HTTP_INTERFACE"
        fi
        
        # Check if http_interface is commented out (defaults to all interfaces)
        if grep -q "^#.*http_interface" "$conf_file" 2>/dev/null; then
            echo -e "${GREEN}   ℹ️  http_interface is commented (defaults to all interfaces)${NC}"
        fi
        
        # Check addons_path
        ADDONS_PATH=$(grep "^addons_path" "$conf_file" 2>/dev/null | head -1 | awk -F'=' '{print $2}' | tr -d ' ')
        if [ -n "$ADDONS_PATH" ]; then
            echo "   Addons Path: $ADDONS_PATH"
        fi
        
        # Show relevant configuration lines
        echo "   Relevant config lines:"
        grep -E "^http_port|^http_interface|^addons_path" "$conf_file" 2>/dev/null | head -3 | sed 's/^/   /'
        
        break
    fi
done

if [ "$ODOO_CONF_FOUND" = false ]; then
    echo -e "${YELLOW}   ⚠️  Odoo config file not found in common locations${NC}"
    if [ -n "$RUNNING_CONF" ]; then
        echo "   Expected location from process: $RUNNING_CONF"
        if [ ! -f "$RUNNING_CONF" ]; then
            echo -e "${RED}   ❌ File does not exist at expected location${NC}"
        fi
    fi
    echo "   Common locations checked:"
    for conf_file in "${ODOO_CONF_FILES[@]}"; do
        if [ -n "$conf_file" ]; then
            if [ -f "$conf_file" ]; then
                echo -e "   ${GREEN}✅ $conf_file${NC}"
            else
                echo "   ❌ $conf_file (not found)"
            fi
        fi
    done
fi
echo ""

# Check 2: Is port 8069 listening?
echo "2. Checking if port 8069 is listening..."
if sudo netstat -tlnp 2>/dev/null | grep :8069 > /dev/null; then
    echo -e "${GREEN}✅ Port 8069 is listening${NC}"
    sudo netstat -tlnp | grep :8069
    LISTENING_INTERFACE=$(sudo netstat -tlnp | grep :8069 | awk '{print $4}')
    if [[ $LISTENING_INTERFACE == *"0.0.0.0"* ]]; then
        echo -e "${GREEN}   ✅ Listening on all interfaces (0.0.0.0) - Accessible from outside${NC}"
    elif [[ $LISTENING_INTERFACE == *"127.0.0.1"* ]]; then
        echo -e "${YELLOW}   ⚠️  Listening only on localhost (127.0.0.1) - Protected by Nginx${NC}"
        echo -e "${GREEN}   ✅ This is OK if Nginx is configured as reverse proxy${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Port 8069 is NOT directly listening${NC}"
    echo "   This is normal if:"
    echo "   - Odoo is behind Nginx reverse proxy"
    echo "   - Odoo listens only on localhost (127.0.0.1)"
    echo "   - Check if Nginx is proxying to Odoo"
fi
echo ""

# Check 3: Firewall status (UFW)
echo "3. Checking UFW firewall..."
if command -v ufw &> /dev/null; then
    UFW_STATUS=$(sudo ufw status | grep -i "Status:" | awk '{print $2}')
    echo "   UFW Status: $UFW_STATUS"
    if sudo ufw status | grep 8069 > /dev/null; then
        echo -e "${GREEN}   ✅ Port 8069 is allowed in UFW${NC}"
        sudo ufw status | grep 8069
    else
        echo -e "${YELLOW}   ⚠️  Port 8069 is NOT explicitly allowed in UFW${NC}"
        echo "   To allow: sudo ufw allow 8069/tcp"
    fi
else
    echo "   UFW is not installed"
fi
echo ""

# Check 4: Test local connection
echo "4. Testing local connection (localhost:8069)..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8069/web/login | grep -q "200\|301\|302"; then
    echo -e "${GREEN}✅ Local connection successful${NC}"
else
    echo -e "${RED}❌ Local connection failed${NC}"
fi
echo ""

# Check 5: Test external connection (if server IP is known)
SERVER_IP="134.122.48.159"
echo "5. Testing external connection ($SERVER_IP:8069)..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://$SERVER_IP:8069/web/login 2>/dev/null)

if [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "301" ] || [ "$HTTP_CODE" == "302" ]; then
    echo -e "${GREEN}✅ External connection successful (HTTP $HTTP_CODE)${NC}"
elif [ "$HTTP_CODE" == "303" ] || [ "$HTTP_CODE" == "307" ]; then
    echo -e "${GREEN}✅ External connection successful (HTTP $HTTP_CODE - Redirect)${NC}"
    echo -e "${GREEN}   ✅ This indicates Nginx is working and redirecting properly${NC}"
elif [ "$HTTP_CODE" == "000" ]; then
    echo -e "${RED}❌ Connection refused or timeout - Port may be blocked by firewall${NC}"
    echo "   Solution: Use Nginx reverse proxy or open port in firewall"
elif [ -n "$HTTP_CODE" ]; then
    echo -e "${YELLOW}⚠️  HTTP Status: $HTTP_CODE${NC}"
    if [ "$HTTP_CODE" == "403" ] || [ "$HTTP_CODE" == "404" ]; then
        echo "   This might indicate Nginx is working but Odoo is not accessible"
    fi
else
    echo -e "${RED}❌ No response from server${NC}"
fi
echo ""

# Check 6: Nginx configuration
echo "6. Checking Nginx configuration..."
NGINX_CONFIGS=(
    "/etc/nginx/sites-available/laft.work"
    "/etc/nginx/sites-available/default"
    "/etc/nginx/nginx.conf"
    "/etc/nginx/conf.d/*.conf"
)

NGINX_FOUND=false

# Check Nginx configs in sites-available
for nginx_conf in /etc/nginx/sites-available/*; do
    if [ -f "$nginx_conf" ] 2>/dev/null; then
        if grep -q "proxy_pass.*8069\|proxy_pass.*odoo" "$nginx_conf" 2>/dev/null; then
            echo -e "${GREEN}✅ Nginx config found: $nginx_conf${NC}"
            echo -e "${GREEN}   ✅ Nginx is configured to proxy Odoo (port 8069)${NC}"
            NGINX_FOUND=true
            # Show relevant lines
            echo "   Relevant configuration:"
            grep -E "proxy_pass|server_name|location" "$nginx_conf" 2>/dev/null | grep -v "^#" | head -5 | sed 's/^/   /'
            break
        fi
    fi
done

# If not found, check sites-enabled
if [ "$NGINX_FOUND" = false ]; then
    for nginx_conf in /etc/nginx/sites-enabled/*; do
        if [ -f "$nginx_conf" ] 2>/dev/null; then
            if grep -q "proxy_pass.*8069\|proxy_pass.*odoo" "$nginx_conf" 2>/dev/null; then
                echo -e "${GREEN}✅ Nginx config found: $nginx_conf${NC}"
                echo -e "${GREEN}   ✅ Nginx is configured to proxy Odoo (port 8069)${NC}"
                NGINX_FOUND=true
                # Show relevant lines
                echo "   Relevant configuration:"
                grep -E "proxy_pass|server_name|location" "$nginx_conf" 2>/dev/null | grep -v "^#" | head -5 | sed 's/^/   /'
                break
            fi
        fi
    done
fi

# If still not found, check conf.d
if [ "$NGINX_FOUND" = false ]; then
    for nginx_conf in /etc/nginx/conf.d/*.conf; do
        if [ -f "$nginx_conf" ] 2>/dev/null; then
            if grep -q "proxy_pass.*8069\|proxy_pass.*odoo" "$nginx_conf" 2>/dev/null; then
                echo -e "${GREEN}✅ Nginx config found: $nginx_conf${NC}"
                echo -e "${GREEN}   ✅ Nginx is configured to proxy Odoo (port 8069)${NC}"
                NGINX_FOUND=true
                # Show relevant lines
                echo "   Relevant configuration:"
                grep -E "proxy_pass|server_name|location" "$nginx_conf" 2>/dev/null | grep -v "^#" | head -5 | sed 's/^/   /'
                break
            fi
        fi
    done
fi

if [ "$NGINX_FOUND" = false ]; then
    # Check if Nginx is running
    if pgrep -x nginx > /dev/null; then
        echo -e "${YELLOW}   ⚠️  Nginx is running but config not found in common locations${NC}"
        echo "   Checking active config..."
        sudo nginx -T 2>/dev/null | grep -E "proxy_pass.*8069|server_name" | head -3 | sed 's/^/   /'
    else
        echo "   Nginx is not running"
    fi
fi
echo ""

# Check 7: Docker container connectivity (if Docker is installed)
if command -v docker &> /dev/null; then
    echo "7. Testing Docker container connectivity..."
    if docker ps | grep whatsapp-bridge > /dev/null; then
        echo "   WhatsApp bridge container is running"
        if docker exec whatsapp-bridge curl -s -o /dev/null -w "%{http_code}" http://$SERVER_IP:8069/web/login | grep -q "200\|301\|302"; then
            echo -e "${GREEN}   ✅ Docker container can reach Odoo${NC}"
        else
            echo -e "${RED}   ❌ Docker container cannot reach Odoo${NC}"
            echo "   Check ODOO_WEBHOOK_URL environment variable"
        fi
    else
        echo "   WhatsApp bridge container is not running"
    fi
    echo ""
fi

# Summary
echo "=========================================="
echo "Summary & Recommendations"
echo "=========================================="
echo ""

LISTENING_INTERFACE=$(sudo netstat -tlnp 2>/dev/null | grep :8069 | awk '{print $4}' | head -1)
NGINX_RUNNING=$(pgrep -x nginx > /dev/null && echo "yes" || echo "no")
EXTERNAL_HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://134.122.48.159:8069/web/login 2>/dev/null)

if [ "$NGINX_RUNNING" == "yes" ] && [ "$EXTERNAL_HTTP_CODE" == "303" ] || [ "$EXTERNAL_HTTP_CODE" == "200" ] || [ "$EXTERNAL_HTTP_CODE" == "302" ]; then
    echo -e "${GREEN}✅ Nginx is working as reverse proxy${NC}"
    echo -e "${GREEN}✅ Odoo is accessible via Nginx (HTTP $EXTERNAL_HTTP_CODE)${NC}"
    echo ""
    echo "📋 Configuration Options:"
    echo ""
    echo "Option 1: Use Nginx (Recommended for production)"
    echo "   ODOO_WEBHOOK_URL=http://localhost:8069/whatsapp/webhook"
    echo "   (Docker container connects to Odoo via localhost)"
    echo ""
    echo "Option 2: Use direct IP (if port 8069 is open)"
    echo "   ODOO_WEBHOOK_URL=http://134.122.48.159:8069/whatsapp/webhook"
    echo ""
    if [[ $LISTENING_INTERFACE == *"127.0.0.1"* ]] || [ -z "$LISTENING_INTERFACE" ]; then
        echo -e "${YELLOW}⚠️  Port 8069 is listening on localhost only${NC}"
        echo "   This is secure and recommended when using Nginx"
        echo "   Use Option 1 above"
    fi
elif [[ $LISTENING_INTERFACE == *"0.0.0.0"* ]]; then
    echo -e "${GREEN}✅ Port 8069 is accessible from outside${NC}"
    echo "   You can use: ODOO_WEBHOOK_URL=http://134.122.48.159:8069/whatsapp/webhook"
elif [[ $LISTENING_INTERFACE == *"127.0.0.1"* ]]; then
    echo -e "${YELLOW}⚠️  Port 8069 is only accessible locally${NC}"
    echo "   Recommended: Use Nginx reverse proxy"
    echo "   OR configure Odoo to listen on 0.0.0.0:8069"
    echo "   Then use: ODOO_WEBHOOK_URL=http://localhost:8069/whatsapp/webhook"
else
    echo -e "${RED}❌ Port 8069 is not listening${NC}"
    echo "   Check Odoo configuration and ensure it's running"
    echo "   Config file should be: /etc/odoo-server.conf"
fi

echo ""
echo "=========================================="
echo "Useful Commands"
echo "=========================================="
echo ""
echo "Odoo Service Management:"
echo "  sudo systemctl status odoo-server.service    # Check service status"
echo "  sudo systemctl start odoo-server.service     # Start Odoo"
echo "  sudo systemctl stop odoo-server.service     # Stop Odoo"
echo "  sudo systemctl restart odoo-server.service   # Restart Odoo"
echo "  sudo systemctl enable odoo-server.service   # Enable on boot"
echo "  sudo journalctl -u odoo-server.service -f   # View logs (follow)"
echo ""
echo "For more information, see README.md Step 4"

