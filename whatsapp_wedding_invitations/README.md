# WhatsApp Wedding Invitations – Deployment Cheatsheet

Use the commands below to reproduce the working setup from this session on a fresh server. Run everything as the `odoo` Linux user unless noted otherwise.

---

## 1. Base system & Python deps

```bash
sudo apt update
sudo apt install -y python3-venv build-essential libxml2-dev libxslt1-dev \
                    libjpeg-dev zlib1g-dev libsasl2-dev libldap2-dev libpq-dev \
                    curl wget git

# From your Odoo venv (if any):
pip install --upgrade pip
pip install qrcode[pil] pillow
```

## 2. Node.js 18 (nvm) – required for whatsapp-web.js

```bash
cd ~
curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc     # or source ~/.profile
nvm install 18
nvm use 18
node -v              # should print v18.x
npm -v
```

## 3. WhatsApp bridge (inside the module folder)

```bash
cd /home/odoo/PycharmProjects/odoo18/odoo18/custom_laft/laft_project/whatsapp_wedding_invitations
npm install
node node_modules/puppeteer/install.js   # ensures Chromium is downloaded
```

### Option A – Dockerized bridge (recommended, install Docker first)

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
sudo usermod -aG docker odoo
newgrp docker
```

Build and run the container:
```bash
cd /home/odoo/PycharmProjects/odoo18/odoo18/custom_laft/laft_project/whatsapp_wedding_invitations
docker build -t whatsapp-bridge .
docker run -d --name whatsapp-bridge -p 3000:3000 \
  -v $(pwd)/.wwebjs_auth:/app/.wwebjs_auth \
  whatsapp-bridge

# Useful Docker helpers
docker ps
docker start whatsapp-bridge
docker logs --tail 40 whatsapp-bridge
docker logs -f whatsapp-bridge
```

### Option B – Run the bridge directly (no Docker)

```bash
cd /home/odoo/PycharmProjects/odoo18/odoo18/custom_laft/laft_project/whatsapp_wedding_invitations
export NVM_DIR="$HOME/.nvm"
. "$NVM_DIR/nvm.sh"
nvm use 18
npm start          # keep this process running (tmux/screen/systemd/pm2)
```

If port 3000 is busy:
```bash
pkill -f whatsapp-server.js
```

## 4. Odoo module installation

1. Restart the Odoo service (or `./odoo-bin --addons-path=...`).
2. Activate developer mode, update app list.
3. Install `WhatsApp Wedding Invitations`.
4. Go to `WhatsApp Invitations > Configuration > Settings` and set:
   - WhatsApp Server URL: `http://localhost:3000`
   - Delay between messages (ms): e.g. `2000`
   - Docker Container Name: `whatsapp-bridge` (match your container)
5. Save and click **Refresh QR Code** (or open `WhatsApp Invitations > WhatsApp Connection` and press **Refresh QR Code**).

## 5. Common troubleshooting commands

```bash
# Verify bridge status
curl http://localhost:3000/api/status

# Regenerate QR directly via API
curl http://localhost:3000/api/qr-code

# Regenerate QR from Odoo shell
odoo shell
>>> self.env['whatsapp.qr.session'].search([], limit=1).action_refresh_qr()

# Reinstall npm deps after Node upgrade
rm -rf node_modules package-lock.json
npm install

# In case Chromium is missing
node node_modules/puppeteer/install.js
```

With the bridge running and the module installed, scanning the QR in Odoo will link WhatsApp Web to the Odoo backend.

## 6. Installer sequence (copy/paste friendly)

1. **Prep OS + Python**
   ```bash
   sudo apt update && sudo apt install -y python3-venv build-essential \
     libxml2-dev libxslt1-dev libjpeg-dev zlib1g-dev libsasl2-dev \
     libldap2-dev libpq-dev curl wget git
   pip install --upgrade pip
   pip install qrcode[pil] pillow
   ```
2. **Install Node 18 via nvm**
   ```bash
   curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
   source ~/.bashrc
   nvm install 18 && nvm use 18
   ```
3. **Install JS deps inside the module**
   ```bash
   cd /home/odoo/PycharmProjects/odoo18/odoo18/custom_laft/laft_project/whatsapp_wedding_invitations
   npm install
   node node_modules/puppeteer/install.js
   ```
4. **Choose runtime**
   - Docker available → install Docker (see section 3), then `docker build` + `docker run`.
   - No Docker → keep `npm start` running via tmux/systemd/pm2.
5. **Configure Odoo**
   - Update app list, install module.
   - `WhatsApp Invitations > Configuration > Settings`: set server URL, delay, container name.
6. **Pair WhatsApp**
   - Open `WhatsApp Invitations > WhatsApp Connection`, click **Refresh QR Code**, scan from your phone.

## 7. Debugger sequence (what to check first)

1. **Verify process**
   - Docker: `docker ps | grep whatsapp-bridge`
   - Bare: `ps -ef | grep whatsapp-bridge` or ensure tmux/systemd unit active.
2. **Inspect logs**
   ```bash
   docker logs --tail 40 whatsapp-bridge
   docker logs -f whatsapp-bridge              # live follow
   ```
   or `journalctl -u whatsapp-bridge.service` / tmux scrollback.
3. **Ping APIs**
   ```bash
   curl http://localhost:3000/api/status
   curl http://localhost:3000/api/qr-code
   ```
   - `ready: true` means already linked; `qrCode` missing → wait/retry.
4. **Check Odoo UI**
   - From QR session form, click **Check Connection** → reads `/api/status`.
   - Use **Refresh QR Code** → forces Docker check + QR regeneration + form reload.
5. **Regenerate manually**
   ```bash
   odoo shell
   >>> session = env['whatsapp.qr.session'].search([], limit=1)
   >>> session.action_refresh_qr()
   ```
6. **Reset Node env**
   ```bash
   rm -rf node_modules package-lock.json
   npm install
   node node_modules/puppeteer/install.js
   ```
   - Needed if Node version changed or puppeteer lost Chromium.
7. **Port issues**
   ```bash
   sudo lsof -i :3000
   pkill -f whatsapp-server.js
   ```
   - Free port 3000 before restarting the bridge.

# WhatsApp Wedding Invitations via n8n (Without Meta)

This solution allows you to send wedding invitations via WhatsApp using n8n without requiring Meta's official WhatsApp Business API. It uses `whatsapp-web.js` which connects to WhatsApp Web.

## 🎯 Features

- ✅ Send personalized wedding invitations via WhatsApp
- ✅ Bulk messaging support for multiple guests
- ✅ No Meta/WhatsApp Business API required
- ✅ Works with n8n workflows
- ✅ Support for text messages and media (images/documents)
- ✅ Personalization with guest names
- ✅ Rate limiting to avoid being blocked
- ✅ QR code authentication

## 📋 Prerequisites

- Node.js (v14 or higher)
- npm or yarn
- n8n installed and running
- A WhatsApp account (personal or business)
- A smartphone to scan QR code

## 🚀 Installation

### 1. Install Dependencies

```bash
cd whatsapp_wedding_invitations
npm install
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env if needed (default port is 3000)
```

### 3. Start the WhatsApp Server

```bash
npm start
```

On first run, you'll see a QR code in the terminal. Scan it with your WhatsApp mobile app:
1. Open WhatsApp on your phone
2. Go to Settings > Linked Devices
3. Tap "Link a Device"
4. Scan the QR code shown in the terminal

Once connected, the server will be ready to send messages.

## 📱 Using with n8n

### Option 1: Import the Pre-built Workflow

1. Open your n8n instance
2. Go to Workflows
3. Click "Import from File"
4. Select `n8n-wedding-invitations-workflow.json`
5. The workflow will be imported with all nodes configured

### Option 2: Manual Setup

1. **Create a Webhook Trigger**
   - Add a Webhook node
   - Set HTTP method to POST
   - Set path to `wedding-invitations`
   - Activate the workflow

2. **Add HTTP Request Node**
   - Method: POST
   - URL: `http://localhost:3000/api/send-bulk`
   - Body Content Type: JSON
   - Body:
   ```json
   {
     "guests": [
       {
         "name": "John Doe",
         "phoneNumber": "1234567890",
         "guestName": "John"
       }
     ],
     "messageTemplate": "Dear {name}, You're invited to our wedding!",
     "delay": 2000
   }
   ```

3. **Add Response Node**
   - Configure to return the API response

## 📝 API Endpoints

### Send Single Message

```bash
POST http://localhost:3000/api/send-message
Content-Type: application/json

{
  "phoneNumber": "1234567890",
  "message": "Your wedding invitation message"
}
```

### Send Message with Media

```bash
POST http://localhost:3000/api/send-media
Content-Type: multipart/form-data

phoneNumber: "1234567890"
message: "Your message"
media: [file upload]
```

Or with URL:

```bash
POST http://localhost:3000/api/send-media
Content-Type: application/json

{
  "phoneNumber": "1234567890",
  "message": "Your message",
  "mediaUrl": "https://example.com/image.jpg"
}
```

### Send Bulk Messages (Wedding Invitations)

```bash
POST http://localhost:3000/api/send-bulk
Content-Type: application/json

{
  "guests": [
    {
      "name": "John Doe",
      "phoneNumber": "1234567890",
      "guestName": "John"
    },
    {
      "name": "Jane Smith",
      "phoneNumber": "0987654321",
      "guestName": "Jane"
    }
  ],
  "messageTemplate": "Dear {name}, You're invited to our wedding on [Date] at [Venue]!",
  "delay": 2000
}
```

### Check Status

```bash
GET http://localhost:3000/api/status
```

### Get QR Code

```bash
GET http://localhost:3000/api/qr-code
```

## 📋 Guest List Format

You can use a CSV file with n8n's CSV node or provide guests as JSON:

**CSV Format:**
```csv
name,phoneNumber,guestName
John Doe,1234567890,John
Jane Smith,0987654321,Jane
```

**JSON Format:**
```json
[
  {
    "name": "John Doe",
    "phoneNumber": "1234567890",
    "guestName": "John"
  },
  {
    "name": "Jane Smith",
    "phoneNumber": "0987654321",
    "guestName": "Jane"
  }
]
```

## 💬 Message Template Variables

In your message template, you can use:
- `{name}` - Full name of the guest
- `{guestName}` - First name or guest name

Example:
```
Dear {name},

You are cordially invited to celebrate our wedding!

Date: [Your Date]
Venue: [Your Venue]

Looking forward to seeing you there!

Best regards,
[Your Names]
```

## 🔧 Phone Number Format

Phone numbers should be provided in international format without the `+` sign:
- ✅ Correct: `1234567890` (US), `919876543210` (India)
- ❌ Wrong: `+1234567890`, `(123) 456-7890`

The system will automatically format them for WhatsApp.

## 📊 Example n8n Workflow Usage

### Trigger via Webhook:

```bash
curl -X POST http://your-n8n-instance/webhook/wedding-invitations \
  -H "Content-Type: application/json" \
  -d '{
    "guests": [
      {
        "name": "John Doe",
        "phoneNumber": "1234567890"
      }
    ],
    "messageTemplate": "Dear {name}, You are invited to our wedding!"
  }'
```

### Using CSV File in n8n:

1. Add a "Read Binary File" node to read your CSV
2. Add a "CSV" node to parse it
3. Add a "Code" node to transform data:
```javascript
const guests = $input.all().map(item => ({
  name: item.json.name,
  phoneNumber: item.json.phoneNumber,
  guestName: item.json.guestName || item.json.name.split(' ')[0]
}));

return [{
  json: {
    guests: guests,
    messageTemplate: "Dear {name}, You're invited!",
    delay: 2000
  }
}];
```
4. Connect to HTTP Request node pointing to your WhatsApp server

## ⚠️ Important Notes

1. **Rate Limiting**: The bulk sender includes a delay between messages (default 2 seconds) to avoid being rate-limited by WhatsApp. Adjust the `delay` parameter if needed.

2. **WhatsApp Terms**: This uses WhatsApp Web protocol. Make sure you comply with WhatsApp's terms of service. Don't spam or send unsolicited messages.

3. **Phone Number Validation**: The system checks if phone numbers are registered on WhatsApp before sending. Invalid numbers will be skipped.

4. **Session Persistence**: Your WhatsApp session is stored in `.wwebjs_auth` directory. Don't delete this folder or you'll need to scan the QR code again.

5. **Server Restart**: If you restart the server, you may need to scan the QR code again if the session expires.

6. **Multiple Instances**: Don't run multiple instances of the server with the same WhatsApp account simultaneously.

## 🐛 Troubleshooting

### QR Code Not Appearing
- Make sure the server started successfully
- Check the terminal for any error messages
- Try accessing `/api/qr-code` endpoint

### Messages Not Sending
- Verify WhatsApp is connected (check `/api/status`)
- Ensure phone numbers are in correct format
- Check if phone numbers are registered on WhatsApp
- Review server logs for error messages

### Connection Lost
- The server will attempt to reconnect automatically
- If persistent, try logging out and scanning QR code again: `POST /api/logout`

## 📄 License

MIT License - Feel free to use and modify as needed.

## 🤝 Support

For issues or questions:
1. Check the server logs
2. Verify all prerequisites are met
3. Ensure WhatsApp is properly connected
4. Review the API responses for error messages

## 🎉 Example Wedding Invitation Message

```
🎉 *Wedding Invitation* 🎉

Dear {name},

You are cordially invited to celebrate our special day!

📅 Date: Saturday, June 15, 2024
📍 Venue: Grand Ballroom, City Hotel
⏰ Time: 6:00 PM

We would be honored to have you join us on this joyous occasion.

Please RSVP by May 1, 2024

Looking forward to celebrating with you!

With love,
John & Jane
```

---

**Note**: This solution is for personal use. For commercial or large-scale messaging, consider using official WhatsApp Business API.

