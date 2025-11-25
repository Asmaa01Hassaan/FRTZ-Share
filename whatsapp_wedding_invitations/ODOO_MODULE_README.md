# WhatsApp Wedding Invitations - Odoo Module

This Odoo module allows you to send wedding invitations via WhatsApp directly from calendar events, without using Meta's WhatsApp Business API.

## Features

- ✅ Send WhatsApp invitations from calendar events
- ✅ Manage event guests with phone numbers
- ✅ Personalized invitation messages
- ✅ Track invitation status (sent/failed/not sent)
- ✅ RSVP status tracking
- ✅ Integration with WhatsApp Web server (no Meta API required)
- ✅ Bulk invitation sending
- ✅ Configurable message templates

## Installation

### 1. Install the WhatsApp Server

First, you need to set up and run the WhatsApp server (Node.js):

```bash
cd whatsapp_wedding_invitations
npm install
npm start
```

When the server starts, scan the QR code with your WhatsApp mobile app to connect.

### 2. Install the Odoo Module

1. Copy this module to your Odoo addons directory (already in `custom_laft/laft_project/`)
2. Update the apps list in Odoo
3. Search for "WhatsApp Wedding Invitations" in Apps
4. Click Install

### 3. Configure WhatsApp Server Settings

1. Go to **Settings** → **WhatsApp Invitations**
2. Set the **WhatsApp Server URL** (default: `http://localhost:3000`)
3. Set the **Delay Between Messages** (default: 2000ms)
4. Click **Test Connection** to verify the server is running

## Usage

### Creating an Event with Guests

1. Go to **Calendar** → **Events**
2. Create a new event or open an existing one
3. Go to the **Guests** tab
4. Add guests with their names and phone numbers:
   - Click **Add a line** in the Guests list
   - Enter guest name
   - Enter phone number (international format, e.g., `1234567890`)
   - Optionally add email and notes

### Sending WhatsApp Invitations

1. Open your event in the calendar
2. Click the **Send WhatsApp Invitations** button in the header
3. A wizard will open showing:
   - Selected guests (only those with phone numbers)
   - Message template (editable)
4. Review and customize the message template if needed
5. Click **Send Invitations**

The system will:
- Send personalized messages to each guest
- Track the status of each invitation
- Show success/failure notifications
- Update guest records with invitation status

### Message Template Variables

You can use these placeholders in your message template:

- `{name}` - Full guest name
- `{guestName}` - First name of guest
- `{event_name}` - Event name
- `{date}` - Event date (formatted)
- `{venue}` - Event location/venue
- `{time}` - Event time (formatted)
- `{organizer}` - Event organizer name

Example template:
```
🎉 *Wedding Invitation* 🎉

Dear {name},

You are cordially invited to celebrate our special day!

📅 Event: {event_name}
📅 Date: {date}
📍 Venue: {venue}
⏰ Time: {time}

We would be honored to have you join us!

With love,
{organizer}
```

### Tracking Invitations

After sending invitations, you can track the status:

- **Not Sent** - Invitation hasn't been sent yet
- **Sent** - Invitation was successfully sent
- **Failed** - Invitation failed (check error message)

You can also track RSVP status:
- **Pending** - No response yet
- **Accepted** - Guest accepted
- **Declined** - Guest declined

## Module Structure

```
whatsapp_wedding_invitations/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── calendar_event.py      # Extends calendar.event
│   ├── event_guest.py          # Guest model
│   └── res_config_settings.py # Settings
├── views/
│   ├── calendar_event_views.xml
│   ├── event_guest_views.xml
│   └── res_config_settings_views.xml
├── wizard/
│   ├── __init__.py
│   ├── whatsapp_invitation_wizard.py
│   └── whatsapp_invitation_wizard_views.xml
├── security/
│   └── ir.model.access.csv
└── whatsapp-server.js          # Node.js server (separate)
```

## Requirements

- Odoo 18.0
- Calendar module (base Odoo module)
- WhatsApp server running (Node.js)
- WhatsApp account connected to the server

## Troubleshooting

### "Cannot connect to WhatsApp server"
- Make sure the WhatsApp server is running (`npm start`)
- Check the server URL in Settings
- Verify the server is accessible from Odoo

### "WhatsApp server is not ready"
- Scan the QR code with your WhatsApp mobile app
- Check server logs for connection issues

### "Invalid phone number format"
- Use international format without + sign (e.g., `1234567890`)
- Remove spaces, dashes, and parentheses
- Ensure the number is registered on WhatsApp

### Invitations not sending
- Check guest phone numbers are valid
- Verify WhatsApp server is connected
- Review error messages in guest records
- Check server logs for detailed errors

## Notes

- The WhatsApp server must be running separately (Node.js process)
- Phone numbers must be registered on WhatsApp
- Rate limiting is applied between messages to avoid being blocked
- The module uses WhatsApp Web protocol (not official Meta API)
- Make sure to comply with WhatsApp's terms of service

## Support

For issues or questions:
1. Check the WhatsApp server logs
2. Review guest invitation error messages
3. Verify server configuration in Settings
4. Test server connection using the Test Connection button





