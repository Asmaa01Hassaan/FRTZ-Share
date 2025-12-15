# 🚀 Quick Deployment Guide for laft.work (134.122.48.159)

## Server Information
- **Server IP**: `134.122.48.159`
- **Domain**: `laft.work`
- **Odoo Config**: `/etc/odoo-server.conf` ✅
- **Addons Path**: `/odoo/custom`
- **Odoo Port**: `8069` (configured to listen on all interfaces)

---

## ✅ Pre-Deployment Checklist

- [ ] SSH access to server
- [ ] Docker installed
- [ ] Python 3.10+ installed
- [ ] Odoo running on port 8069

---

## 📦 Step-by-Step Installation

### 1. Copy Module to Server

```bash
# From your local machine
scp -r whatsapp_wedding_invitations root@134.122.48.159:/odoo/custom/

# Or clone directly on server
ssh root@134.122.48.159
cd /odoo/custom
git clone <your-repo-url> whatsapp_wedding_invitations
```

### 2. Install Python Dependencies

```bash
# SSH to server
ssh root@134.122.48.159

# Install Python packages
pip install qrcode[pil] pillow pdf2image python-barcode

# Install system dependencies
sudo apt install -y poppler-utils
```

### 3. Check Port 8069 Status

```bash
cd /odoo/custom/whatsapp_wedding_invitations
chmod +x check-port-8069.sh
./check-port-8069.sh
```

**Expected output:**
- ✅ Odoo is running
- ✅ Port 8069 listening on 0.0.0.0
- ✅ Firewall allows port 8069 (or configure it)

**If port is blocked:**
```bash
sudo ufw allow 8069/tcp
sudo ufw reload
```

### 4. Build and Run Docker Container

```bash
cd /odoo/custom/whatsapp_wedding_invitations

# Build Docker image
docker build -t whatsapp-bridge .

# Run container with correct webhook URL
docker run -d \
  --name whatsapp-bridge \
  --restart unless-stopped \
  -p 3000:3000 \
  -e ODOO_WEBHOOK_URL=http://134.122.48.159:8069/whatsapp/webhook \
  -v $(pwd)/.wwebjs_auth:/app/.wwebjs_auth \
  whatsapp-bridge
```

### 5. Verify Docker Container

```bash
# Check container is running
docker ps | grep whatsapp-bridge

# Check logs
docker logs --tail 50 whatsapp-bridge

# Test API
curl http://localhost:3000/api/status
```

### 6. Verify Odoo Service

```bash
# Check Odoo service status
sudo systemctl status odoo-server.service

# If not running, start it
sudo systemctl start odoo-server.service

# Enable on boot (optional)
sudo systemctl enable odoo-server.service
```

### 7. Install Module in Odoo

1. **Restart Odoo** (to load new module):
```bash
sudo systemctl restart odoo-server.service
# OR
sudo systemctl restart odoo
# OR
sudo service odoo restart
```

2. **In Odoo UI**:
   - Go to `Apps` menu
   - Click `Update Apps List`
   - Search for `WhatsApp Wedding Invitations`
   - Click `Install`

### 8. Configure Module Settings

1. Go to: `Settings > WhatsApp Wedding Invitations`
2. Set:
   - **WhatsApp Server URL**: `http://localhost:3000`
   - **Message Delay**: `2000`
   - **Docker Container Name**: `whatsapp-bridge`
3. Save

### 9. Connect WhatsApp

1. Go to: `WhatsApp Invitations > WhatsApp Connection`
2. Click **Refresh QR Code**
3. Scan QR code with your phone
4. Wait for "Ready" status

### 10. Test Everything

```bash
# Test webhook from server
curl -X POST http://134.122.48.159:8069/whatsapp/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "params": {
      "phoneNumber": "201111106797",
      "message": "نعم",
      "senderName": "Test Guest"
    }
  }'

# Test from Docker container
docker exec whatsapp-bridge curl -s http://134.122.48.159:8069/web/login
```

---

## 🔧 Troubleshooting

### Port 8069 Not Accessible

```bash
# Check if listening
sudo netstat -tlnp | grep 8069

# Open firewall
sudo ufw allow 8069/tcp
sudo ufw reload

# Verify Odoo config
grep "http_interface" /etc/odoo-server.conf
# Should be empty or 0.0.0.0
```

### Docker Container Cannot Reach Odoo

```bash
# Check environment variable
docker inspect whatsapp-bridge | grep ODOO_WEBHOOK_URL

# Test connectivity
docker exec whatsapp-bridge curl -v http://134.122.48.159:8069/web/login

# Recreate with correct URL
docker stop whatsapp-bridge && docker rm whatsapp-bridge
docker run -d \
  --name whatsapp-bridge \
  --restart unless-stopped \
  -p 3000:3000 \
  -e ODOO_WEBHOOK_URL=http://134.122.48.159:8069/whatsapp/webhook \
  -v $(pwd)/.wwebjs_auth:/app/.wwebjs_auth \
  whatsapp-bridge
```

### Module Not Appearing in Odoo

```bash
# Check module is in correct location
ls -la /odoo/custom/whatsapp_wedding_invitations/__manifest__.py

# Check addons_path in odoo-server.conf
grep "addons_path" /etc/odoo-server.conf

# Check Odoo service status
sudo systemctl status odoo-server.service

# Restart Odoo
sudo systemctl restart odoo-server.service

# View logs if there are errors
sudo journalctl -u odoo-server.service -n 50

# Update apps list in Odoo UI
```

---

## 📋 Useful Commands

```bash
# Odoo Service Management
sudo systemctl status odoo-server.service    # Check service status
sudo systemctl start odoo-server.service     # Start Odoo
sudo systemctl stop odoo-server.service      # Stop Odoo
sudo systemctl restart odoo-server.service   # Restart Odoo
sudo systemctl enable odoo-server.service   # Enable on boot
sudo journalctl -u odoo-server.service -f   # View logs (follow)

# View Docker logs
docker logs -f whatsapp-bridge

# Restart Docker container
docker restart whatsapp-bridge

# Check Odoo logs (alternative)
tail -f /var/log/odoo/odoo.log

# Check port status
./check-port-8069.sh

# Test webhook
curl -X POST http://134.122.48.159:8069/whatsapp/webhook \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","params":{"phoneNumber":"201111106797","message":"test"}}'
```

---

## ✅ Final Verification Checklist

- [ ] Module copied to `/odoo/custom/whatsapp_wedding_invitations/`
- [ ] Python dependencies installed
- [ ] Port 8069 is open and accessible
- [ ] Docker container running
- [ ] Module installed in Odoo
- [ ] Settings configured
- [ ] WhatsApp connected (QR scanned)
- [ ] Test message sent successfully
- [ ] Auto-reply working

---

## 🆘 Need Help?

1. Run diagnostic script: `./check-port-8069.sh`
2. Check Docker logs: `docker logs whatsapp-bridge`
3. Check Odoo logs: `tail -f /var/log/odoo/odoo.log`
4. See full README.md for detailed troubleshooting

---

**Last Updated**: Based on Odoo config with `http_interface =` (empty = all interfaces)

