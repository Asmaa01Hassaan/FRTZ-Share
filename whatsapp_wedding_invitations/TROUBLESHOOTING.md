# WhatsApp Wedding Invitations - Troubleshooting Guide

## Common Problems and Solutions

---

### Problem 1: Webhook returns 404

**Symptoms:**
```
curl http://localhost:8069/whatsapp/webhook/http
# Returns: 404 Not Found
```

**Cause:** `dbfilter` is not set or using wrong parameter name (`db_filter` instead of `dbfilter`)

**Solution:**
```bash
# Check current setting
grep -n "dbfilter\|db_filter" /etc/odoo-server.conf

# Fix if using wrong name
sudo sed -i 's/^db_filter/dbfilter/' /etc/odoo-server.conf

# Add if missing
echo 'dbfilter = ^omevent$' | sudo tee -a /etc/odoo-server.conf

# Restart Odoo
sudo systemctl restart odoo-server.service
```

---

### Problem 2: WhatsApp shows "fetch failed"

**Symptoms:**
```
Error calling Odoo webhook: fetch failed
```

**Cause:** Docker container cannot reach Odoo

**Solution:**
```bash
# 1. Check Docker network mode
docker inspect whatsapp-bridge | grep NetworkMode
# Should be "host"

# 2. Check ODOO_WEBHOOK_URL
docker inspect whatsapp-bridge | grep ODOO_WEBHOOK_URL
# Should be: http://127.0.0.1:8069/whatsapp/webhook/http

# 3. Recreate container with correct settings
docker stop whatsapp-bridge
docker rm whatsapp-bridge
docker run -d \
  --name whatsapp-bridge \
  --network host \
  --restart unless-stopped \
  -e ODOO_WEBHOOK_URL=http://127.0.0.1:8069/whatsapp/webhook/http \
  -e ODOO_DB_NAME=omevent \
  -v /odoo/custom/mahara/whatsapp_wedding_invitations/.wwebjs_auth:/app/.wwebjs_auth \
  whatsapp-bridge
```

---

### Problem 3: WhatsApp not connected

**Symptoms:**
```
WhatsApp client state is null, not CONNECTED
```

**Solution:**
1. Open Odoo in browser
2. Go to: WhatsApp Invitations > WhatsApp Connection
3. Click "Refresh QR Code"
4. Scan with WhatsApp on your phone
5. Wait for "Ready" status

---

### Problem 4: Auto-reply not sent

**Symptoms:**
- Message received but no auto-reply
- Guest status not updated

**Cause:** Guest not found or message not recognized

**Solution:**
```bash
# 1. Check if guest exists with that phone
# In Odoo: Calendar > Configuration > Guests

# 2. Check phone number format
# Should be stored without + or country code spaces
# Example: 201111106797 (not +20 111 110 6797)

# 3. Check Odoo logs
tail -50 /var/log/odoo/odoo-server.log | grep -i "guest\|whatsapp"
```

---

### Problem 5: Session corrupted

**Symptoms:**
```
Error: sendIq called before startComms
Error: Cannot read properties of undefined (reading 'WidFactory')
```

**Solution:**
```bash
# Delete session and restart
docker stop whatsapp-bridge
rm -rf /odoo/custom/mahara/whatsapp_wedding_invitations/.wwebjs_auth
docker start whatsapp-bridge

# Then scan QR code again
```

---

## Quick Diagnostic Commands

```bash
# Check Odoo status
sudo systemctl status odoo-server.service

# Check WhatsApp container
docker ps | grep whatsapp
docker logs --tail 20 whatsapp-bridge

# Test webhook
curl -s -X POST http://localhost:8069/whatsapp/webhook/http \
  -H "Content-Type: application/json" \
  -d '{"phoneNumber":"201111106797","message":"نعم","senderName":"Test"}'

# Check dbfilter
grep "dbfilter" /etc/odoo-server.conf

# Check Odoo logs
tail -50 /var/log/odoo/odoo-server.log | grep -i "whatsapp\|webhook"
```

---

## Configuration Checklist

| Setting | Location | Correct Value |
|---------|----------|---------------|
| `dbfilter` | `/etc/odoo-server.conf` | `^omevent$` |
| `ODOO_WEBHOOK_URL` | Docker env | `http://127.0.0.1:8069/whatsapp/webhook/http` |
| Docker network | Docker run | `--network host` |
| Module installed | Odoo Apps | `whatsapp_wedding_invitations` ✓ |

---

## Restart All Services Script

```bash
# Use the restart script
cd /odoo/custom/mahara/whatsapp_wedding_invitations
sudo ./restart_services.sh
```

---

## Support

If problems persist after trying these solutions:
1. Run health check: `./health_check.sh`
2. Collect logs from both Odoo and WhatsApp
3. Check the exact error message

