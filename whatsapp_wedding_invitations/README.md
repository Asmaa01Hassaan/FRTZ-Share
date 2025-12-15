# WhatsApp Wedding Invitations – Complete Deployment Guide

A comprehensive Odoo 18 module for sending wedding invitations via WhatsApp with automatic RSVP tracking, attendee management, and barcode generation.

---

## 🎯 Features

### Core Features
- ✅ Send personalized wedding invitations via WhatsApp
- ✅ Bulk messaging support for multiple guests
- ✅ No Meta/WhatsApp Business API required (uses whatsapp-web.js)
- ✅ QR code authentication for WhatsApp Web
- ✅ Support for text messages and media (images/documents)
- ✅ Personalization with guest names

### RSVP & Attendance Features
- ✅ **Automatic RSVP Processing**: Guests can reply "نعم" (yes) or "لا" (no) via WhatsApp
- ✅ **Auto-Reply System**: Automatic barcode image sent when guest confirms attendance
- ✅ **Multiple Reply Support**: Allows up to 4 auto-replies per guest for positive responses
- ✅ **Attendee Auto-Creation**: Automatically creates `event.registration` records when RSVP status changes to "accepted"
- ✅ **Barcode Generation**: Generates unique barcodes for each attendee for event check-in
- ✅ **QR Code Generation**: Generates QR codes from attendee barcodes

### Guest Matching Features
- ✅ **Phone Number Matching**: Supports various international formats (with/without country codes)
- ✅ **Name-Based Fallback**: Falls back to sender name matching when phone lookup fails
- ✅ **WhatsApp LID Support**: Handles WhatsApp Business Linked IDs

---

## 📋 Prerequisites

### System Requirements
- Ubuntu 20.04+ / Debian 11+
- Python 3.10+
- Node.js 18+ (via nvm)
- Docker (recommended) or npm
- PostgreSQL 14+
- Odoo 18

### Python Dependencies
```bash
pip install qrcode[pil] pillow pdf2image python-barcode
```

### System Libraries (for pdf2image)
```bash
sudo apt install -y poppler-utils
```

---

## 🚀 Installation

### 1. Base System & Python Dependencies

```bash
sudo apt update
sudo apt install -y python3-venv build-essential libxml2-dev libxslt1-dev \
                    libjpeg-dev zlib1g-dev libsasl2-dev libldap2-dev libpq-dev \
                    curl wget git poppler-utils

# From your Odoo venv (if any):
pip install --upgrade pip
pip install qrcode[pil] pillow pdf2image python-barcode
```

### 2. Node.js 18 (via nvm) – Required for whatsapp-web.js

```bash
cd ~
curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc     # or source ~/.profile
nvm install 18
nvm use 18
node -v              # should print v18.x
npm -v
```

### 3. WhatsApp Bridge Setup

```bash
cd /path/to/whatsapp_wedding_invitations
npm install
node node_modules/puppeteer/install.js   # ensures Chromium is downloaded
```

### 4. Docker Installation (Recommended)

If Docker is missing:
```bash
sudo apt install -y ca-certificates gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io
sudo usermod -aG docker $USER
newgrp docker
```

---

## 🌐 Production Server Deployment (laft.work)

> **📌 Quick Start**: For a step-by-step deployment guide, see [DEPLOYMENT_QUICK_START.md](DEPLOYMENT_QUICK_START.md)

### Server Information
- **Server IP**: `134.122.48.159`
- **Domain**: `laft.work`
- **Odoo URL**: `https://laft.work/odoo`
- **Odoo Config Path**: `/etc/odoo-server.conf` ✅
- **Addons Path**: `/odoo/custom`

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│              Production Server (134.122.48.159)                  │
│                                                                  │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────────┐  │
│  │   Nginx     │───▶│    Odoo      │◀──▶│   PostgreSQL      │  │
│  │  (Reverse   │    │  (Port 8069) │    │                   │  │
│  │   Proxy)    │    └──────────────┘    └───────────────────┘  │
│  │             │           ▲                                    │
│  │  Port 443   │           │                                    │
│  │  (HTTPS)    │           │ HTTP (internal)                    │
│  └─────────────┘           │                                    │
│         │                  ▼                                    │
│         │         ┌──────────────────┐                          │
│         └────────▶│  WhatsApp Bridge │                          │
│                   │  Docker Container│                          │
│                   │  (Port 3000)     │                          │
│                   └──────────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

### Step 1: Copy Module to Server

**Based on your Odoo config**, the `addons_path` includes `/odoo/custom`, so copy the module there:

```bash
# From local machine
scp -r /path/to/whatsapp_wedding_invitations root@134.122.48.159:/odoo/custom/

# Or use git
ssh root@134.122.48.159
cd /odoo/custom
git clone <your-repo-url> whatsapp_wedding_invitations
```

**Verify the module is in the correct location**:
```bash
# On server
ls -la /odoo/custom/whatsapp_wedding_invitations/
# Should show: __manifest__.py, models/, views/, etc.
```

**Note**: Your `addons_path` is:
```
/odoo/odoo-server/odoo/addons,/odoo/odoo-server/addons,/odoo/enterprise/addons,/odoo/custom
```

So the module should be at: `/odoo/custom/whatsapp_wedding_invitations/`

### Step 2: Install Python Dependencies on Server

```bash
# SSH to server
ssh root@134.122.48.159

# Activate Odoo virtual environment (if using one)
source /path/to/odoo-venv/bin/activate

# Install dependencies
pip install qrcode[pil] pillow pdf2image python-barcode

# Install system dependencies
sudo apt install -y poppler-utils
```

### Step 3: Build and Run Docker Container

```bash
cd /odoo/custom/whatsapp_wedding_invitations

# Build the Docker image
docker build -t whatsapp-bridge .

# ⚠️ IMPORTANT: Choose the correct ODOO_WEBHOOK_URL based on your setup!
```

#### Scenario A: Nginx is Running (Recommended)

If Nginx is working (HTTP 303 response), Odoo is likely listening on `localhost:8069`:

```bash
# Use localhost - Docker container connects to Odoo via localhost
docker run -d \
  --name whatsapp-bridge \
  --restart unless-stopped \
  -p 3000:3000 \
  -e ODOO_WEBHOOK_URL=http://localhost:8069/whatsapp/webhook \
  -v $(pwd)/.wwebjs_auth:/app/.wwebjs_auth \
  whatsapp-bridge
```

#### Scenario B: Direct Port Access

If port 8069 is directly accessible (no Nginx or Nginx not configured):

```bash
# Use server IP directly
docker run -d \
  --name whatsapp-bridge \
  --restart unless-stopped \
  -p 3000:3000 \
  -e ODOO_WEBHOOK_URL=http://134.122.48.159:8069/whatsapp/webhook \
  -v $(pwd)/.wwebjs_auth:/app/.wwebjs_auth \
  whatsapp-bridge
```

**💡 How to determine which scenario?**
Run `./check-port-8069.sh` and check:
- If Nginx is detected → Use Scenario A (localhost)
- If port 8069 is listening on 0.0.0.0 → Use Scenario B (server IP)

#### ⚠️ CRITICAL: Environment Variable Configuration

The `ODOO_WEBHOOK_URL` environment variable tells the WhatsApp bridge where to send incoming messages.

| Scenario | ODOO_WEBHOOK_URL Value |
|----------|------------------------|
| **laft.work (RECOMMENDED)** | `http://134.122.48.159:8069/whatsapp/webhook` |
| Docker on same server (localhost) | `http://localhost:8069/whatsapp/webhook` |
| Docker with host networking | `http://127.0.0.1:8069/whatsapp/webhook` |
| Docker default bridge (Linux) | `http://172.17.0.1:8069/whatsapp/webhook` |
| Using domain (HTTPS) | `https://laft.work/whatsapp/webhook` |

**🚀 For laft.work production (134.122.48.159):**
```bash
# ✅ RECOMMENDED: Using server IP directly
docker run -d \
  --name whatsapp-bridge \
  --restart unless-stopped \
  -p 3000:3000 \
  -e ODOO_WEBHOOK_URL=http://134.122.48.159:8069/whatsapp/webhook \
  -v $(pwd)/.wwebjs_auth:/app/.wwebjs_auth \
  whatsapp-bridge

# Option 2: Using localhost (if Docker and Odoo on same server)
docker run -d \
  --name whatsapp-bridge \
  --restart unless-stopped \
  -p 3000:3000 \
  --network host \
  -e ODOO_WEBHOOK_URL=http://localhost:8069/whatsapp/webhook \
  -v $(pwd)/.wwebjs_auth:/app/.wwebjs_auth \
  whatsapp-bridge

# Option 3: Using HTTPS domain (requires SSL configured)
docker run -d \
  --name whatsapp-bridge \
  --restart unless-stopped \
  -p 3000:3000 \
  -e ODOO_WEBHOOK_URL=https://laft.work/whatsapp/webhook \
  -v $(pwd)/.wwebjs_auth:/app/.wwebjs_auth \
  whatsapp-bridge
```

### Step 4: Verify Port 8069 is Open

#### Your Current Odoo Configuration

Based on your `odoo.conf`:
```ini
http_port = 8069
http_interface =          # Empty = listens on all interfaces (0.0.0.0) ✅
addons_path = ...,/odoo/custom
```

**✅ Good News**: 
- Port 8069 is configured ✅
- `http_interface` is empty = Odoo listens on **all interfaces** (0.0.0.0) ✅
- This means Odoo is accessible from outside (if firewall allows) ✅
- **Config file location**: `/etc/odoo-server.conf` ✅

**⚠️ Important Notes**:
1. **If Nginx is running**: Odoo might be listening on `127.0.0.1:8069` (localhost only) for security
2. **HTTP 303 response**: This indicates Nginx is working as reverse proxy ✅
3. **To check your config**: `cat /etc/odoo-server.conf | grep -E "http_port|http_interface"`

**What you need to check**:
1. Run `./check-port-8069.sh` to see detailed status
2. If Nginx is working, use `ODOO_WEBHOOK_URL=http://localhost:8069/whatsapp/webhook` in Docker
3. If port 8069 is directly accessible, use `ODOO_WEBHOOK_URL=http://134.122.48.159:8069/whatsapp/webhook`

#### Quick Check Script

We've included a script to automatically check port 8069 status:

```bash
# Make script executable (if not already)
chmod +x check-port-8069.sh

# Run the check script
./check-port-8069.sh
```

This script will check:
- ✅ If Odoo is running
- ✅ If port 8069 is listening
- ✅ Firewall status (UFW)
- ✅ Local and external connectivity
- ✅ Nginx configuration
- ✅ Docker container connectivity

#### Option A: Check if Port is Listening (Local)

```bash
# SSH to server
ssh root@134.122.48.159

# Check if Odoo is listening on port 8069
sudo netstat -tlnp | grep 8069
# OR
sudo ss -tlnp | grep 8069
# OR
sudo lsof -i :8069

# Expected output should show:
# tcp  0  0  0.0.0.0:8069  0.0.0.0:*  LISTEN  <pid>/odoo-bin
# OR
# tcp  0  0  127.0.0.1:8069  0.0.0.0:*  LISTEN  <pid>/odoo-bin
```

**⚠️ Important**: 
- If you see `0.0.0.0:8069` → Port is accessible from outside ✅
- If you see `127.0.0.1:8069` → Port is only accessible locally (use Nginx reverse proxy)

#### Option B: Check Firewall (UFW)

```bash
# Check UFW status
sudo ufw status

# If port 8069 is not open, add it:
sudo ufw allow 8069/tcp
sudo ufw reload

# Verify
sudo ufw status | grep 8069
```

#### Option C: Check Firewall (iptables)

   ```bash
# List iptables rules
sudo iptables -L -n | grep 8069

# If port is blocked, allow it:
sudo iptables -A INPUT -p tcp --dport 8069 -j ACCEPT
sudo iptables-save
```

#### Option D: Test from External Machine

   ```bash
# From your local machine (NOT the server)
curl -v http://134.122.48.159:8069/web/login

# If successful, you'll see HTTP response
# If failed, you'll see "Connection refused" or timeout
```

#### Option E: Test from Docker Container

   ```bash
# Test if Docker container can reach Odoo
docker exec whatsapp-bridge curl -s http://134.122.48.159:8069/web/login

# If successful, you'll see HTML response
# If failed, check network configuration
```

### Step 5: Configure Nginx (Recommended for Production)

**Why use Nginx?**
- ✅ Security: Hide Odoo port from public
- ✅ SSL/HTTPS: Encrypt traffic
- ✅ Better performance
- ✅ Single entry point

Add to your Nginx configuration for `laft.work`:

```nginx
# /etc/nginx/sites-available/laft.work

server {
    listen 443 ssl http2;
    server_name laft.work;
    
    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/laft.work/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/laft.work/privkey.pem;
    
    # Odoo main application
    location / {
        proxy_pass http://127.0.0.1:8069;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (for Odoo longpolling)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # WhatsApp webhook endpoint (important for external access)
    location /whatsapp/webhook {
        proxy_pass http://127.0.0.1:8069/whatsapp/webhook;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
    }
    
    # WhatsApp Bridge API (internal only - optional)
    # Uncomment if you need external access to WhatsApp API
    # location /whatsapp-api/ {
    #     proxy_pass http://127.0.0.1:3000/api/;
    #     proxy_set_header Host $host;
    #     proxy_set_header X-Real-IP $remote_addr;
    # }
}
```

Reload Nginx:
   ```bash
sudo nginx -t
sudo systemctl reload nginx
```

#### Alternative: Configure Odoo to Listen on All Interfaces

**✅ Good News**: Based on your current Odoo configuration:
```ini
http_port = 8069
http_interface =          # Empty = listens on all interfaces (0.0.0.0)
```

This means Odoo is **already configured to listen on all interfaces**! ✅

**However**, you still need to:
1. **Open port 8069 in firewall**:
   ```bash
sudo ufw allow 8069/tcp
sudo ufw reload
   ```

2. **Verify it's working**:
   ```bash
sudo netstat -tlnp | grep 8069
# Should show: 0.0.0.0:8069
```

**If you need to change the configuration**:

1. **Edit Odoo configuration file** (`/etc/odoo-server.conf`):
```ini
[options]
http_port = 8069
http_interface = 0.0.0.0    # Or leave empty for all interfaces
# OR for localhost only:
# http_interface = 127.0.0.1  # Use with Nginx reverse proxy
```

2. **Or start Odoo with parameters**:
```bash
./odoo-bin --http-interface=0.0.0.0 --http-port=8069
```

3. **Restart Odoo**:
```bash
sudo systemctl restart odoo-server.service
# OR
sudo systemctl restart odoo
# OR
sudo service odoo restart
```

4. **Verify**:
```bash
sudo netstat -tlnp | grep 8069
# Should show: 0.0.0.0:8069 (not 127.0.0.1:8069)
```

### Step 6: Verify Odoo Service Status

```bash
# Check Odoo service status
sudo systemctl status odoo-server.service

# Check if service is running
sudo systemctl is-active odoo-server.service

# Check if service is enabled (starts on boot)
sudo systemctl is-enabled odoo-server.service

# View Odoo logs
sudo journalctl -u odoo-server.service -f
```

**Expected output**:
- `active (running)` - Service is running ✅
- `inactive (dead)` - Service is stopped ❌
- `enabled` - Service starts on boot ✅
- `disabled` - Service does not start on boot ⚠️

### Step 7: Configure Odoo Module Settings

1. Go to `Settings > WhatsApp Wedding Invitations`
2. Set:
   - **WhatsApp Server URL**: `http://localhost:3000` (internal Docker access)
   - **Message Delay**: `2000` (2 seconds between messages)
   - **Docker Container Name**: `whatsapp-bridge`

3. Go to `WhatsApp Invitations > WhatsApp Connection`
4. Click **Refresh QR Code**
5. Scan with your phone

### Step 8: Verify Installation

```bash
# Check Docker container is running
docker ps | grep whatsapp-bridge

# Check container logs
docker logs --tail 50 whatsapp-bridge

# Test WhatsApp API status
curl http://localhost:3000/api/status

# Test Odoo webhook (from server) - using server IP
curl -X POST http://134.122.48.159:8069/whatsapp/webhook \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","params":{"phoneNumber":"201111106797","message":"test","senderName":"Test"}}'

# Or test via localhost
curl -X POST http://localhost:8069/whatsapp/webhook \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","params":{"phoneNumber":"201111106797","message":"test","senderName":"Test"}}'
```

---

## 🔧 Configuration Reference

### Environment Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `ODOO_WEBHOOK_URL` | URL for Odoo webhook | `http://172.17.0.1:8018/whatsapp/webhook` | `http://localhost:8069/whatsapp/webhook` |
| `PORT` | WhatsApp server port | `3000` | `3000` |
| `PUPPETEER_EXECUTABLE_PATH` | Path to Chrome/Chromium | auto-detect | `/usr/bin/chromium` |

### Odoo System Parameters

Set via `Settings > Technical > Parameters > System Parameters`:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `whatsapp.server_url` | WhatsApp bridge URL | `http://localhost:3000` |
| `whatsapp.message_delay` | Delay between messages (ms) | `2000` |
| `whatsapp.docker_container_name` | Docker container name | `whatsapp-bridge` |
| `web.base.url` | Odoo base URL | `https://laft.work` |

---

## 📞 Phone Number Formats

The system supports various phone number formats for maximum compatibility:

### Supported Formats
| Country | Format | Example |
|---------|--------|---------|
| Egypt | With country code | `201111106797` |
| Egypt | Without country code | `01111106797` |
| KSA | With country code | `966592155935` |
| KSA | With + prefix | `+966592155935` |
| UAE | With country code | `971501234567` |

### Matching Logic
The system attempts to match incoming WhatsApp messages using:
1. **Exact match** - Full phone number
2. **Normalized match** - After removing country codes (966, 20, 971)
3. **Last 10/9/8 digits** - For partial matches
4. **Name-based fallback** - Uses WhatsApp sender name if phone lookup fails

### WhatsApp Business LID Issue
⚠️ **Important**: WhatsApp Business accounts may send Linked IDs (LID) instead of real phone numbers (e.g., `202262928478247@lid`). In this case:
- The system falls back to **sender name matching**
- Ensure guest names in Odoo match WhatsApp display names exactly

---

## 🔄 Auto-Reply System

### How It Works
1. Guest receives invitation via WhatsApp
2. Guest replies with "نعم" (yes) or "لا" (no)
3. System processes the response:
   - Updates RSVP status
   - Creates `event.registration` record (for "نعم")
   - Generates barcode for attendee
   - Sends barcode image as auto-reply

### Response Keywords
| Response | Keywords | Action |
|----------|----------|--------|
| Accept | نعم, اه, ايوه, yes, ok, اكيد, طبعا, ان شاء الله, إن شاء الله, حاضر, حاضرين, موافق, تمام, هحضر, جاي, جايين | Set status to `accepted`, send barcode |
| Decline | لا, لأ, no, مش هينفع, مش هقدر, للاسف, معلش, مقدرش | Set status to `declined` |

### Auto-Reply Limits
- Maximum 4 auto-replies per guest for positive responses
- Prevents spam if guest sends multiple "نعم" messages
- Counter resets if guest status changes

---

## 🎫 Barcode & QR Code Generation

### Automatic Generation
When a guest's RSVP status changes to "accepted":
1. `event.registration` record is created
2. Unique barcode is generated
3. QR code image is generated from barcode
4. Barcode image is sent via WhatsApp auto-reply

### Manual Generation
From the Event Registration form:
- Click **"Generate Badge Image"** button
- View barcode and QR code in the "Barcode & QR Code" section

### Dependencies
```bash
pip install python-barcode qrcode[pil] pillow
```

---

## 🐳 Docker Commands

### Container Management
```bash
# Check container status
docker ps | grep whatsapp-bridge

# Start container
docker start whatsapp-bridge

# Stop container
docker stop whatsapp-bridge

# Restart container
docker restart whatsapp-bridge

# View logs
docker logs --tail 50 whatsapp-bridge
docker logs -f whatsapp-bridge  # Follow logs

# View environment variables
docker inspect whatsapp-bridge | grep -A 20 "Env"
```

### Update WhatsApp Server Code
```bash
# Copy updated whatsapp-server.js to container
docker cp /path/to/whatsapp-server.js whatsapp-bridge:/app/whatsapp-server.js

# Restart container to apply changes
docker restart whatsapp-bridge
```

### Recreate Container with New Settings
```bash
# Stop and remove old container
docker stop whatsapp-bridge
docker rm whatsapp-bridge

# Run with new settings
docker run -d \
  --name whatsapp-bridge \
  --restart unless-stopped \
  -p 3000:3000 \
  -e ODOO_WEBHOOK_URL=http://localhost:8069/whatsapp/webhook \
  -v $(pwd)/.wwebjs_auth:/app/.wwebjs_auth \
  whatsapp-bridge
```

---

## 🔍 API Endpoints

### Check Status
```bash
curl http://localhost:3000/api/status
```

### Get QR Code
```bash
curl http://localhost:3000/api/qr-code
```

### Send Single Message
```bash
curl -X POST http://localhost:3000/api/send-message \
  -H "Content-Type: application/json" \
  -d '{"phoneNumber": "201111106797", "message": "Your wedding invitation"}'
```

### Send Message with Media
```bash
curl -X POST http://localhost:3000/api/send-media \
  -H "Content-Type: application/json" \
  -d '{
    "phoneNumber": "201111106797",
    "message": "Your message",
    "mediaBase64": "base64_encoded_image",
    "mimetype": "image/png",
    "filename": "barcode.png"
  }'
```

---

## 🐛 Troubleshooting

### Common Production Issues

#### 1. Webhook Not Receiving Messages
```bash
# Check if Odoo is accessible from Docker
docker exec whatsapp-bridge curl -s http://172.17.0.1:8069/whatsapp/webhook

# Check Docker logs for webhook errors
docker logs whatsapp-bridge 2>&1 | grep -i "webhook\|error"

# Verify ODOO_WEBHOOK_URL is set correctly
docker inspect whatsapp-bridge | grep ODOO_WEBHOOK_URL
```

**Fix**: Recreate container with correct `ODOO_WEBHOOK_URL`:
```bash
docker stop whatsapp-bridge && docker rm whatsapp-bridge
docker run -d --name whatsapp-bridge -p 3000:3000 \
  -e ODOO_WEBHOOK_URL=http://134.122.48.159:8069/whatsapp/webhook \
  -v $(pwd)/.wwebjs_auth:/app/.wwebjs_auth \
  whatsapp-bridge
```

#### 2. QR Code Not Appearing
```bash
# Check server status
curl http://localhost:3000/api/status

# Check logs
docker logs --tail 50 whatsapp-bridge
```

#### 3. Auto-Reply Not Working
Check Odoo logs for:
```
📥 Received WhatsApp message from XXXXXXX: "نعم"
🔍 Finding guest by phone: original=XXXXXXX
✅ Found X guests: ['Guest Name']
```

If you see "Guest not found":
- Verify guest phone number matches
- Check if sender name matches guest name (for LID fallback)

#### 4. Connection Refused Errors

**Problem**: Docker container cannot reach Odoo webhook.

**Diagnosis**:
```bash
# 1. Check if Odoo is running
curl http://localhost:8069/web/login

# 2. Check if Odoo is listening on correct interface
sudo netstat -tlnp | grep 8069
# If shows 127.0.0.1:8069 → Only local access (use Nginx or change to 0.0.0.0)
# If shows 0.0.0.0:8069 → Accessible from outside ✅

# 3. Check firewall
sudo ufw status
sudo iptables -L -n | grep 8069

# 4. Test from Docker container
docker exec whatsapp-bridge curl -v http://134.122.48.159:8069/web/login

# 5. Test from external machine
curl -v http://134.122.48.159:8069/web/login
```

**Solutions**:

**Solution 1: Use Nginx (Recommended)**
- Configure Nginx as reverse proxy (see Step 5)
- Use `ODOO_WEBHOOK_URL=http://localhost:8069/whatsapp/webhook` in Docker
- Nginx handles external access via HTTPS

**Solution 2: Open Port Directly**
```bash
# Allow port 8069 in firewall
sudo ufw allow 8069/tcp
sudo ufw reload

# Configure Odoo to listen on all interfaces
# Edit odoo.conf:
xmlrpc_interface = 0.0.0.0
xmlrpc_port = 8069

# Restart Odoo
sudo systemctl restart odoo
```

**Solution 3: Use Docker Host Network**
```bash
# Recreate container with host network
docker stop whatsapp-bridge && docker rm whatsapp-bridge
docker run -d \
  --name whatsapp-bridge \
  --restart unless-stopped \
  --network host \
  -e ODOO_WEBHOOK_URL=http://localhost:8069/whatsapp/webhook \
  -v $(pwd)/.wwebjs_auth:/app/.wwebjs_auth \
  whatsapp-bridge
```

#### 5. SSL/Certificate Issues (for HTTPS webhook)
If using `https://laft.work/whatsapp/webhook`:
```bash
# Test SSL
curl -v https://laft.work/whatsapp/webhook

# Check certificate
openssl s_client -connect laft.work:443 -servername laft.work
```

### Debug Commands
```bash
# Check Odoo logs
tail -f /var/log/odoo/odoo.log | grep whatsapp

# Check Docker logs
docker logs -f whatsapp-bridge

# Test webhook manually
curl -X POST http://localhost:8069/whatsapp/webhook \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","params":{"phoneNumber":"201111106797","message":"نعم","senderName":"Test Guest"}}'

# Check Docker network
docker network inspect bridge
```

---

## 📊 Database Schema

### event.guest
| Field | Type | Description |
|-------|------|-------------|
| name | Char | Guest name |
| phone_number | Char | Phone number |
| rsvp_status | Selection | pending/accepted/declined |
| auto_reply_count | Integer | Number of auto-replies sent |
| calendar_event_id | Many2one | Related calendar event |
| event_registration_ids | One2many | Related event registrations |

### event.registration (Extended)
| Field | Type | Description |
|-------|------|-------------|
| barcode | Char | Unique barcode |
| barcode_image | Binary | Generated barcode image |
| barcode_qr_image | Binary | Generated QR code image |
| badge_image | Binary | Generated badge PDF as image |
| guest_id | Many2one | Related guest record |

---

## 🔐 Security Considerations

1. **WhatsApp Terms**: This uses WhatsApp Web protocol. Comply with WhatsApp's terms of service.
2. **Rate Limiting**: Default 2-second delay between messages to avoid blocking.
3. **Session Persistence**: WhatsApp session stored in `.wwebjs_auth` directory.
4. **Webhook Security**: The `/whatsapp/webhook` endpoint is public. Consider:
   - IP whitelisting in Nginx
   - Adding authentication token
   - Rate limiting

### Secure Webhook (Optional)
Add to Nginx:
```nginx
location /whatsapp/webhook {
    # Only allow from Docker network
    allow 172.17.0.0/16;
    allow 127.0.0.1;
    deny all;
    
    proxy_pass http://127.0.0.1:8069/whatsapp/webhook;
    # ... other proxy settings
}
```

---

## 📝 Production Checklist

Before going live on `laft.work`:

- [ ] Python dependencies installed (`qrcode`, `pillow`, `pdf2image`, `python-barcode`)
- [ ] System dependencies installed (`poppler-utils`)
- [ ] Docker installed and running
- [ ] WhatsApp bridge container built and running
- [ ] `ODOO_WEBHOOK_URL` environment variable set correctly
- [ ] Nginx configured (if using reverse proxy)
- [ ] Module installed in Odoo
- [ ] WhatsApp Server URL configured in Odoo settings
- [ ] QR code scanned and WhatsApp connected
- [ ] Test message sent successfully
- [ ] Auto-reply tested with "نعم" response
- [ ] Barcode generation working

---

## 📝 Changelog

### Version 18.0.1.0.0
- Initial release
- WhatsApp Web integration
- Guest management
- RSVP tracking
- Auto-reply system
- Barcode/QR code generation
- Name-based fallback matching
- WhatsApp LID support
- Multiple auto-reply support (max 4)
- Production deployment documentation

---

## 📄 License

LGPL-3 - Feel free to use and modify as needed.

---

## 🎉 Example Wedding Invitation Message

```
🎉 *دعوة زفاف* 🎉

عزيزي/عزيزتي {name}،

يسعدنا دعوتكم لحضور حفل زفافنا!

📅 التاريخ: السبت، 15 يونيو 2024
📍 المكان: قاعة الاحتفالات الكبرى
⏰ الوقت: 6:00 مساءً

للتأكيد، الرجاء الرد بـ:
✅ "نعم" للحضور
❌ "لا" للاعتذار

في انتظار تشريفكم!

مع أطيب التحيات،
العروسين
```

---

## 🆘 Support

For issues specific to `laft.work` (134.122.48.159) deployment:
1. Check Docker container logs: `docker logs whatsapp-bridge`
2. Check Odoo logs: `tail -f /var/log/odoo/odoo.log`
3. Verify network connectivity: `curl http://134.122.48.159:8069/web/login`
4. Ensure `ODOO_WEBHOOK_URL` is set to `http://134.122.48.159:8069/whatsapp/webhook`
5. Check Docker environment: `docker inspect whatsapp-bridge | grep ODOO_WEBHOOK_URL`

---

**Note**: This solution is for personal use. For commercial or large-scale messaging, consider using official WhatsApp Business API.
