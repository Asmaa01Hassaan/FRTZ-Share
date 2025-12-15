# WhatsApp Wedding Invitations - Project Analysis

## 📋 Executive Summary

This is a comprehensive Odoo 18 module that enables sending wedding invitations via WhatsApp without requiring Meta's official WhatsApp Business API. The solution uses `whatsapp-web.js` library to connect to WhatsApp Web, providing a cost-effective alternative for personal/small-scale wedding invitation management.

**Version:** 18.0.1.0.0  
**Category:** Marketing/Events  
**License:** LGPL-3  
**Dependencies:** Odoo base, calendar, event modules

---

## 🏗️ Architecture Overview

The project follows a **hybrid architecture** with two main components:

### 1. **Odoo Module (Python Backend)**
- Extends Odoo's `calendar.event` and `event.event` models
- Manages guest data, invitation templates, and status tracking
- Provides UI for event management and invitation sending
- Communicates with WhatsApp server via HTTP REST API

### 2. **WhatsApp Bridge Server (Node.js)**
- Standalone Express.js server running on port 3000
- Uses `whatsapp-web.js` library to connect to WhatsApp Web
- Handles QR code generation for authentication
- Processes message sending requests from Odoo
- Can run as Docker container or standalone process

```
┌─────────────┐         HTTP REST API         ┌──────────────────┐
│   Odoo 18   │◄─────────────────────────────►│  WhatsApp Bridge │
│   Module    │                                │   (Node.js)      │
│  (Python)   │                                │   Port 3000      │
└─────────────┘                                └────────┬─────────┘
                                                       │
                                                       │ WhatsApp Web Protocol
                                                       ▼
                                              ┌──────────────────┐
                                              │   WhatsApp Web   │
                                              │   (via Browser)  │
                                              └──────────────────┘
```

---

## 📦 Project Structure

```
whatsapp_wedding_invitations/
├── __init__.py                    # Module initialization
├── __manifest__.py                # Module metadata
├── models/                        # Odoo models
│   ├── __init__.py
│   ├── calendar_event.py          # Extends calendar.event
│   ├── event_event.py             # Extends event.event
│   ├── event_guest.py             # Guest model (event.guest)
│   ├── event_registration.py      # Extends event.registration
│   ├── res_config_settings.py    # Settings configuration
│   └── whatsapp_qr_session.py    # QR code session management
├── wizard/                         # Invitation wizard
│   ├── __init__.py
│   ├── whatsapp_invitation_wizard.py
│   └── whatsapp_invitation_wizard_views.xml
├── views/                         # Odoo views
│   ├── calendar_event_views.xml
│   ├── event_event_views.xml
│   ├── event_guest_views.xml
│   ├── res_config_settings_views.xml
│   └── whatsapp_qr_session_views.xml
├── security/
│   └── ir.model.access.csv       # Access rights
├── static/                        # Frontend assets
│   └── src/
│       ├── css/
│       ├── js/
│       └── xml/
├── whatsapp-server.js             # Node.js WhatsApp bridge
├── package.json                   # Node.js dependencies
├── Dockerfile                     # Docker containerization
├── README.md                      # Deployment guide
└── ODOO_MODULE_README.md          # Module documentation
```

---

## 🔧 Core Components

### 1. **Odoo Models**

#### `event.guest` (New Model)
- **Purpose:** Stores guest information for calendar events
- **Key Fields:**
  - `name`: Guest full name
  - `phone_number`: Phone number (international format)
  - `email`: Optional email
  - `invitation_status`: not_sent/sent/failed
  - `invitation_sent_date`: Timestamp
  - `invitation_error`: Error message if failed
  - `message_id`: WhatsApp message ID
  - `rsvp_status`: pending/accepted/declined
- **Relations:** Many2one to `calendar.event`

#### `calendar.event` (Extended)
- **New Fields:**
  - `event_guest_ids`: One2many to `event.guest`
  - `guest_count`: Computed count
  - `invitation_sent_count`: Computed statistic
  - `invitation_failed_count`: Computed statistic
  - `invitation_message_template`: Message template with placeholders
  - `invitation_image`: Binary field for invitation image
  - `invitation_image_url`: Public URL for image
- **New Methods:**
  - `action_send_whatsapp_invitations()`: Opens invitation wizard

#### `event.event` (Extended)
- **New Fields:**
  - `whatsapp_message_template`: Default invitation template
  - `whatsapp_registration_count`: Count of registrations with phone
  - `whatsapp_invitation_sent_count`: Sent invitations count
  - `whatsapp_invitation_failed_count`: Failed invitations count
- **New Methods:**
  - `action_send_whatsapp_invitations()`: Opens wizard for event registrations

#### `event.registration` (Extended)
- **New Fields:**
  - `whatsapp_invitation_status`: Status tracking
  - `whatsapp_invitation_sent_date`: Timestamp
  - `whatsapp_invitation_error`: Error message
  - `whatsapp_message_id`: Message ID
- **New Methods:**
  - `_format_phone_number_for_whatsapp()`: Phone number formatting

#### `whatsapp.qr.session` (New Model)
- **Purpose:** Manages WhatsApp QR code sessions
- **Key Fields:**
  - `qr_code_image`: Binary QR code image
  - `qr_code_text`: Raw QR code data
  - `status`: disconnected/qr_ready/connected
- **Key Methods:**
  - `action_refresh_qr()`: Fetches QR code from server
  - `action_check_status()`: Checks connection status
  - `action_restart_container()`: Restarts Docker container

#### `res.config.settings` (Extended)
- **Configuration Fields:**
  - `whatsapp_server_url`: Server URL (default: http://localhost:3000)
  - `whatsapp_delay_between_messages`: Delay in milliseconds
  - `whatsapp_bridge_container_name`: Docker container name
- **Key Methods:**
  - `action_test_whatsapp_connection()`: Tests server connection
  - `action_fetch_whatsapp_qr_code()`: Fetches QR code

### 2. **Wizard Component**

#### `whatsapp.invitation.wizard`
- **Purpose:** Transient model for sending invitations
- **Key Fields:**
  - `event_id`: Related calendar event
  - `guest_ids`: Many2many to guests
  - `message_template`: Editable message template
  - `invitation_image`: Optional image attachment
  - `send_mode`: text_only/with_image
- **Key Methods:**
  - `action_send_invitations()`: Main sending logic
  - `_personalize_message()`: Template replacement
  - `_compress_image()`: Image optimization
  - `_send_message_with_image()`: Send with media
  - `_send_text_message()`: Send text only

### 3. **WhatsApp Bridge Server**

#### `whatsapp-server.js` (Node.js/Express)
- **Technology Stack:**
  - Express.js for HTTP server
  - whatsapp-web.js for WhatsApp Web protocol
  - Puppeteer for browser automation
  - QRCode libraries for QR generation

- **API Endpoints:**
  - `GET /api/status`: Check server and connection status
  - `GET /api/qr-code`: Get QR code for authentication
  - `POST /api/send-message`: Send text message
  - `POST /api/send-media`: Send message with media
  - `POST /api/send-bulk`: Send bulk messages
  - `POST /api/logout`: Logout and reset session

- **Features:**
  - QR code generation and display
  - Phone number validation
  - WhatsApp registration check
  - Rate limiting support
  - Automatic reconnection
  - Session persistence (`.wwebjs_auth`)

---

## ✨ Key Features

### 1. **Event Management**
- ✅ Create events with guest lists
- ✅ Manage guest information (name, phone, email)
- ✅ Track invitation status per guest
- ✅ RSVP status tracking
- ✅ Invitation statistics (sent/failed counts)

### 2. **Message Personalization**
- ✅ Template-based messages with placeholders:
  - `{name}`: Full guest name
  - `{guestName}`: First name
  - `{event_name}`: Event name
  - `{date}`: Formatted event date
  - `{venue}`: Event location
  - `{time}`: Formatted event time
  - `{organizer}`: Organizer name
  - `{image_url}`: Image URL (if provided)

### 3. **Image Support**
- ✅ Attach invitation images
- ✅ Automatic image compression (max 1MB)
- ✅ Support for JPG, PNG, GIF formats
- ✅ Fallback to text-only if image fails
- ✅ Image URL support in messages

### 4. **Bulk Sending**
- ✅ Send invitations to multiple guests
- ✅ Configurable delay between messages
- ✅ Individual status tracking per guest
- ✅ Error handling and reporting

### 5. **Connection Management**
- ✅ QR code authentication
- ✅ Connection status checking
- ✅ Docker container management
- ✅ Automatic container startup
- ✅ Session persistence

### 6. **Error Handling**
- ✅ Phone number validation
- ✅ WhatsApp registration check
- ✅ Connection error handling
- ✅ Detailed error messages per guest
- ✅ Fallback mechanisms

---

## 🔄 Data Flow

### Sending Invitations Flow:

```
1. User creates/opens calendar event
   ↓
2. User adds guests with phone numbers
   ↓
3. User clicks "Send WhatsApp Invitations"
   ↓
4. Wizard opens with:
   - Selected guests (with phone numbers)
   - Message template (editable)
   - Optional image
   ↓
5. User reviews and clicks "Send Invitations"
   ↓
6. Wizard checks server status
   ↓
7. For each guest:
   a. Personalize message template
   b. Format phone number
   c. Send HTTP request to WhatsApp bridge
   d. Update guest record with status
   e. Wait for delay
   ↓
8. Show results notification
```

### WhatsApp Bridge Flow:

```
1. Server starts → Initialize WhatsApp client
   ↓
2. Generate QR code → Display in terminal/API
   ↓
3. User scans QR code with WhatsApp mobile
   ↓
4. Client authenticated → Ready to send
   ↓
5. Receive send request from Odoo
   ↓
6. Validate phone number
   ↓
7. Check if number is registered on WhatsApp
   ↓
8. Send message via WhatsApp Web
   ↓
9. Return result to Odoo
```

---

## 🛠️ Technical Stack

### Backend (Odoo)
- **Language:** Python 3.x
- **Framework:** Odoo 18.0
- **Dependencies:**
  - `qrcode[pil]`: QR code generation
  - `Pillow`: Image processing
  - Standard library: `urllib`, `json`, `base64`, `subprocess`

### WhatsApp Bridge
- **Language:** JavaScript (Node.js)
- **Runtime:** Node.js 18+
- **Framework:** Express.js
- **Key Dependencies:**
  - `whatsapp-web.js`: WhatsApp Web protocol
  - `puppeteer`: Browser automation
  - `qrcode`: QR code generation
  - `qrcode-terminal`: Terminal QR display
  - `express`: HTTP server
  - `cors`: CORS support
  - `multer`: File upload handling

### Deployment
- **Containerization:** Docker
- **Base Image:** node:18-bullseye
- **Browser:** Chromium (for Puppeteer)

---

## 🔌 Integration Points

### 1. **Odoo ↔ WhatsApp Bridge**
- **Protocol:** HTTP REST API
- **Communication:** JSON payloads
- **Endpoints:**
  - Status checking
  - QR code fetching
  - Message sending
  - Media sending

### 2. **WhatsApp Bridge ↔ WhatsApp Web**
- **Protocol:** WhatsApp Web protocol (via whatsapp-web.js)
- **Authentication:** QR code scanning
- **Session:** Stored in `.wwebjs_auth` directory

### 3. **Odoo Models Integration**
- Extends `calendar.event` (Odoo Calendar module)
- Extends `event.event` (Odoo Events module)
- Extends `event.registration` (Odoo Events module)
- Extends `res.config.settings` (Odoo Settings)

---

## 📊 Database Schema

### New Tables:
1. **`event_guest`**
   - Guest information for calendar events
   - Foreign key to `calendar_event`

2. **`whatsapp_qr_session`**
   - QR code session management
   - Stores QR code images and status

### Extended Tables:
1. **`calendar_event`**
   - Added guest relationship and invitation fields

2. **`event_event`**
   - Added WhatsApp invitation fields

3. **`event_registration`**
   - Added WhatsApp invitation tracking fields

---

## ⚙️ Configuration

### System Parameters (ir.config_parameter):
- `whatsapp_wedding_invitations.server_url`: WhatsApp server URL
- `whatsapp_wedding_invitations.delay_between_messages`: Delay in ms
- `whatsapp_wedding_invitations.docker_container`: Container name

### Environment Variables (Node.js):
- `PORT`: Server port (default: 3000)
- `PUPPETEER_SKIP_DOWNLOAD`: Skip Chromium download
- `PUPPETEER_EXECUTABLE_PATH`: Chromium path

---

## 🎯 Use Cases

1. **Wedding Planning**
   - Create wedding event
   - Add guest list with phone numbers
   - Send personalized invitations via WhatsApp
   - Track RSVP responses

2. **Event Management**
   - Corporate events
   - Birthday parties
   - Anniversaries
   - Any event requiring WhatsApp invitations

3. **Bulk Messaging**
   - Send to multiple recipients
   - Personalized messages
   - Image attachments
   - Status tracking

---

## 🔍 Code Quality Analysis

### Strengths ✅

1. **Well-Structured Code**
   - Clear separation of concerns
   - Modular design
   - Proper Odoo conventions

2. **Error Handling**
   - Comprehensive try-catch blocks
   - User-friendly error messages
   - Fallback mechanisms

3. **Documentation**
   - Extensive README files
   - Code comments
   - Deployment guides

4. **Flexibility**
   - Configurable settings
   - Template-based messages
   - Multiple sending modes

5. **User Experience**
   - Wizard-based interface
   - Status tracking
   - Progress notifications

### Potential Issues ⚠️

1. **Missing Model Import**
   - `event_event.py` is not imported in `models/__init__.py`
   - This could cause the model not to load

2. **Phone Number Formatting**
   - Inconsistent formatting across models
   - `event_guest.py` has `_format_phone_number()`
   - `event_registration.py` has `_format_phone_number_for_whatsapp()`
   - Could benefit from a shared utility

3. **Image Compression**
   - Complex compression logic in wizard
   - Could be extracted to a utility method
   - PIL dependency not always available

4. **Docker Dependency**
   - Hard dependency on Docker for container management
   - No graceful fallback if Docker unavailable
   - Could use systemd or other process managers

5. **Rate Limiting**
   - Fixed delay between messages
   - No adaptive rate limiting
   - Could hit WhatsApp limits with large lists

6. **Session Management**
   - QR code sessions may expire
   - No automatic refresh mechanism
   - Manual intervention required

7. **Security Considerations**
   - WhatsApp server URL not validated
   - No authentication on WhatsApp bridge API
   - Sensitive data in logs potentially

8. **Error Recovery**
   - Limited retry logic
   - No queue system for failed messages
   - Manual retry required

---

## 🚀 Recommendations

### Immediate Fixes

1. **Fix Model Import**
   ```python
   # In models/__init__.py, add:
   from . import event_event
   ```

2. **Standardize Phone Formatting**
   - Create a shared utility method
   - Use consistent formatting across all models

3. **Add Error Logging**
   - Implement proper logging
   - Store errors in database for analysis

### Enhancements

1. **Queue System**
   - Implement message queue for failed sends
   - Automatic retry mechanism
   - Scheduled retry jobs

2. **Rate Limiting**
   - Implement adaptive rate limiting
   - Respect WhatsApp's rate limits
   - Exponential backoff on errors

3. **Authentication**
   - Add API key authentication to WhatsApp bridge
   - Secure communication between Odoo and bridge

4. **Monitoring**
   - Add health check endpoints
   - Metrics collection
   - Performance monitoring

5. **Testing**
   - Unit tests for models
   - Integration tests for wizard
   - API tests for WhatsApp bridge

6. **Documentation**
   - API documentation
   - Architecture diagrams
   - Troubleshooting guide

### Scalability

1. **Multi-Instance Support**
   - Support multiple WhatsApp accounts
   - Load balancing for bridge server
   - Session management per account

2. **Caching**
   - Cache QR codes
   - Cache connection status
   - Reduce API calls

3. **Async Processing**
   - Background jobs for sending
   - Non-blocking operations
   - Better user experience

---

## 📝 Deployment Checklist

- [ ] Install Node.js 18+
- [ ] Install Python dependencies (qrcode, pillow)
- [ ] Install npm dependencies
- [ ] Build Docker image (optional)
- [ ] Start WhatsApp bridge server
- [ ] Configure Odoo settings
- [ ] Scan QR code with WhatsApp
- [ ] Test connection
- [ ] Create test event
- [ ] Send test invitation

---

## 🔐 Security Considerations

1. **WhatsApp Terms of Service**
   - Ensure compliance with WhatsApp ToS
   - Don't spam or send unsolicited messages
   - Respect rate limits

2. **Data Privacy**
   - Guest phone numbers stored in database
   - Ensure GDPR compliance if applicable
   - Secure storage of session data

3. **Network Security**
   - Use HTTPS in production
   - Secure communication between Odoo and bridge
   - Firewall rules for port 3000

4. **Access Control**
   - Review security access rules
   - Limit who can send invitations
   - Audit trail for sent messages

---

## 📈 Performance Considerations

1. **Bulk Sending**
   - Current implementation sends sequentially
   - Could be slow for large guest lists
   - Consider batch processing

2. **Image Compression**
   - Compression happens synchronously
   - Could block for large images
   - Consider async compression

3. **Database Queries**
   - Some computed fields may cause N+1 queries
   - Consider optimizing with prefetch

4. **API Calls**
   - Multiple HTTP requests per invitation
   - Consider batching or connection pooling

---

## 🎓 Learning Resources

- **Odoo Documentation:** https://www.odoo.com/documentation/
- **whatsapp-web.js:** https://github.com/pedroslopez/whatsapp-web.js
- **Express.js:** https://expressjs.com/
- **Puppeteer:** https://pptr.dev/

---

## 📞 Support & Maintenance

### Common Issues:

1. **QR Code Not Appearing**
   - Check Docker container status
   - Verify server is running
   - Check logs for errors

2. **Messages Not Sending**
   - Verify WhatsApp connection
   - Check phone number format
   - Review error messages

3. **Connection Lost**
   - Restart Docker container
   - Rescan QR code
   - Check network connectivity

---

## 📄 License

- **Odoo Module:** LGPL-3
- **WhatsApp Bridge:** MIT (based on dependencies)

---

## 🎯 Conclusion

This is a well-architected solution for sending WhatsApp invitations from Odoo. It provides a good balance between functionality and simplicity, avoiding the complexity and cost of Meta's official API. The code is generally well-structured, but could benefit from some improvements in error handling, testing, and scalability.

**Overall Assessment:** ⭐⭐⭐⭐ (4/5)

**Recommended for:**
- Small to medium-scale event management
- Personal wedding planning
- Organizations needing WhatsApp integration without Meta API

**Not recommended for:**
- Large-scale commercial messaging
- High-volume automated messaging
- Production environments requiring SLA guarantees

---

*Analysis generated on: 2024*
*Project Version: 18.0.1.0.0*




