# -*- coding: utf-8 -*-

import uuid
import secrets
import base64
import json
import urllib.request
import urllib.error
import logging
import time
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class EventGuest(models.Model):
    _name = 'event.guest'
    _description = 'Event Guest'
    _order = 'name'

    name = fields.Char(
        string='Guest Name',
        required=True,
        help='Full name of the guest'
    )
    
    phone_number = fields.Char(
        string='Phone Number',
        required=True,
        help='Phone number in international format (e.g., 1234567890)'
    )
    
    email = fields.Char(
        string='Email',
        help='Email address of the guest'
    )
    
    wedding_event_id = fields.Many2one(
        'wedding.event',
        string='Wedding Event',
        ondelete='cascade',
        index=True
    )
    
    calendar_event_id = fields.Many2one(
        'calendar.event',
        string='Calendar Event',
        ondelete='cascade',
        index=True
    )
    
    event_id = fields.Reference(
        selection=[
            ('wedding.event', 'Wedding Event'),
            ('calendar.event', 'Calendar Event'),
        ],
        string='Event',
        compute='_compute_event_id',
        inverse='_inverse_event_id',
        store=False,
        domain=[]  # Empty domain to prevent Odoo from trying to evaluate active_id
    )
    
    @api.depends('wedding_event_id', 'calendar_event_id')
    def _compute_event_id(self):
        """Compute event_id from wedding_event_id or calendar_event_id"""
        for guest in self:
            if guest.wedding_event_id:
                # Only set if the record is saved (not a NewId)
                try:
                    event_id = guest.wedding_event_id.id
                    if isinstance(event_id, int) and event_id > 0:
                        guest.event_id = f'wedding.event,{event_id}'
                    else:
                        guest.event_id = False
                except (ValueError, TypeError):
                    guest.event_id = False
            elif guest.calendar_event_id:
                # Only set if the record is saved (not a NewId)
                try:
                    event_id = guest.calendar_event_id.id
                    if isinstance(event_id, int) and event_id > 0:
                        guest.event_id = f'calendar.event,{event_id}'
                    else:
                        guest.event_id = False
                except (ValueError, TypeError):
                    guest.event_id = False
            else:
                guest.event_id = False
    
    def _inverse_event_id(self):
        """Inverse method to set wedding_event_id or calendar_event_id from event_id"""
        for guest in self:
            if guest.event_id:
                model, res_id = guest.event_id.split(',')
                res_id = int(res_id)
                if model == 'wedding.event':
                    guest.wedding_event_id = res_id
                    guest.calendar_event_id = False
                elif model == 'calendar.event':
                    guest.calendar_event_id = res_id
                    guest.wedding_event_id = False
            else:
                guest.wedding_event_id = False
                guest.calendar_event_id = False
    
    invitation_status = fields.Selection([
        ('not_sent', 'Not Sent'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ], string='Invitation Status', default='not_sent', required=True)
    
    invitation_sent_date = fields.Datetime(
        string='Invitation Sent Date',
        help='Date and time when invitation was sent'
    )
    
    invitation_error = fields.Text(
        string='Error Message',
        help='Error message if invitation failed'
    )
    
    message_id = fields.Char(
        string='WhatsApp Message ID',
        help='ID of the sent WhatsApp message'
    )
    
    # RSVP / Attendance fields
    rsvp_status = fields.Selection([
        ('pending', 'Pending'),
        ('accepted', 'Will Attend ✅'),
        ('declined', 'Will Not Attend ❌'),
    ], string='RSVP Status', default='pending', tracking=True)
    
    rsvp_response_date = fields.Datetime(
        string='Response Date',
        help='Date and time when guest responded'
    )
    
    rsvp_response_method = fields.Selection([
        ('link', 'Via Link'),
        ('whatsapp', 'Via WhatsApp'),
        ('manual', 'Manual Entry'),
    ], string='Response Method')
    
    auto_reply_count = fields.Integer(
        string='Auto-Reply Count',
        default=0,
        help='Number of times auto-reply has been sent to this guest'
    )
    
    confirmation_token = fields.Char(
        string='Confirmation Token',
        help='Unique token for confirmation links',
        copy=False,
        index=True
    )
    
    confirmation_sent = fields.Boolean(
        string='Confirmation Request Sent',
        default=False
    )
    
    confirmation_sent_date = fields.Datetime(
        string='Confirmation Sent Date'
    )
    
    companions_count = fields.Integer(
        string='Number of Companions',
        default=0,
        help='Number of people accompanying the guest'
    )
    
    total_attendees = fields.Integer(
        string='Total Attendees',
        compute='_compute_total_attendees',
        store=True,
        help='Total number of people (guest + companions)'
    )
    
    rsvp_message = fields.Text(
        string='Guest Message',
        help='Message from guest when responding'
    )
    
    # Computed URL fields for display with widget="url"
    confirm_url = fields.Char(
        string='Confirm URL',
        compute='_compute_confirmation_urls',
        help='Click to open confirmation page'
    )
    
    decline_url = fields.Char(
        string='Decline URL',
        compute='_compute_confirmation_urls',
        help='Click to open decline page'
    )
    
    notes = fields.Text(
        string='Notes',
        help='Additional notes about the guest'
    )
    
    # Link to event registrations created from this guest
    event_registration_ids = fields.One2many(
        'event.registration',
        'guest_id',
        string='Event Registrations',
        help='Event registrations created from this guest'
    )
    
    # Related fields from event registration for barcode and QR code
    registration_barcode = fields.Char(
        string='Registration Barcode',
        compute='_compute_registration_barcode',
        store=False,
        help='Barcode from the first event registration'
    )
    
    registration_barcode_image = fields.Binary(
        string='Registration Barcode Image',
        compute='_compute_registration_barcode',
        store=False,
        help='Barcode image from the first event registration'
    )
    
    registration_barcode_qr_image = fields.Binary(
        string='Registration QR Code',
        compute='_compute_registration_barcode',
        store=False,
        help='QR code image from the first event registration'
    )
    
    @api.depends('event_registration_ids.barcode', 'event_registration_ids.barcode_image', 'event_registration_ids.barcode_qr_image')
    def _compute_registration_barcode(self):
        """Get barcode and images from the first event registration"""
        for guest in self:
            # Get the first registration (main guest registration)
            first_registration = guest.event_registration_ids.filtered(lambda r: r.state != 'cancel')[:1]
            if first_registration:
                guest.registration_barcode = first_registration.barcode
                guest.registration_barcode_image = first_registration.barcode_image
                guest.registration_barcode_qr_image = first_registration.barcode_qr_image
            else:
                guest.registration_barcode = False
                guest.registration_barcode_image = False
                guest.registration_barcode_qr_image = False
    
    @api.depends('confirmation_token')
    def _compute_confirmation_urls(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
        # Ensure URL has protocol
        if not base_url.startswith('http'):
            base_url = 'https://' + base_url
        base_url = base_url.rstrip('/')
        
        for guest in self:
            if guest.confirmation_token:
                guest.confirm_url = f"{base_url}/wedding/confirm/{guest.confirmation_token}"
                guest.decline_url = f"{base_url}/wedding/decline/{guest.confirmation_token}"
            else:
                guest.confirm_url = False
                guest.decline_url = False
    
    @api.depends('companions_count', 'rsvp_status')
    def _compute_total_attendees(self):
        for guest in self:
            if guest.rsvp_status == 'accepted':
                guest.total_attendees = 1 + guest.companions_count
            else:
                guest.total_attendees = 0
    
    @api.model
    def create(self, vals):
        """Set default invitation status and generate confirmation token"""
        if 'invitation_status' not in vals:
            vals['invitation_status'] = 'not_sent'
        if 'confirmation_token' not in vals:
            vals['confirmation_token'] = self._generate_token()
        
        # Ensure at least one event_id is set
        if 'calendar_event_id' not in vals and 'wedding_event_id' not in vals:
            # Try to get from context
            if 'default_calendar_event_id' in self.env.context:
                vals['calendar_event_id'] = self.env.context['default_calendar_event_id']
            elif 'default_wedding_event_id' in self.env.context:
                vals['wedding_event_id'] = self.env.context['default_wedding_event_id']
        
        guest = super(EventGuest, self).create(vals)
        
        # If created with RSVP status 'accepted', create event registrations
        if guest.rsvp_status == 'accepted':
            guest._create_event_registrations()
        
        return guest
    
    def _generate_token(self):
        """Generate a unique confirmation token"""
        return secrets.token_urlsafe(16)
    
    def regenerate_token(self):
        """Regenerate confirmation token"""
        for guest in self:
            guest.confirmation_token = self._generate_token()
    
    def _format_phone_number(self):
        """Format phone number for WhatsApp (remove non-digits)"""
        self.ensure_one()
        if not self.phone_number:
            return None
        # Remove all non-digit characters
        cleaned = ''.join(filter(str.isdigit, self.phone_number))
        return cleaned if cleaned else None
    
    def get_confirmation_url(self, short=True):
        """Get the confirmation URL for this guest"""
        self.ensure_one()
        if not self.confirmation_token:
            self.regenerate_token()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
        # Ensure URL has protocol
        if not base_url.startswith('http'):
            base_url = 'https://' + base_url
        # Remove trailing slash
        base_url = base_url.rstrip('/')
        # Use short URL format for better WhatsApp compatibility
        path = '/c/' if short else '/wedding/confirm/'
        return f"{base_url}{path}{self.confirmation_token}"
    
    def get_decline_url(self, short=True):
        """Get the decline URL for this guest"""
        self.ensure_one()
        if not self.confirmation_token:
            self.regenerate_token()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
        # Ensure URL has protocol
        if not base_url.startswith('http'):
            base_url = 'https://' + base_url
        # Remove trailing slash
        base_url = base_url.rstrip('/')
        # Use short URL format for better WhatsApp compatibility
        path = '/d/' if short else '/wedding/decline/'
        return f"{base_url}{path}{self.confirmation_token}"
    
    def action_confirm_attendance(self, method='manual', message=None, companions=0, skip_registration=False):
        """Mark guest as confirmed"""
        ctx = {'skip_event_registration': skip_registration} if skip_registration else {}
        self.with_context(**ctx).write({
            'rsvp_status': 'accepted',
            'rsvp_response_date': fields.Datetime.now(),
            'rsvp_response_method': method,
            'rsvp_message': message,
            'companions_count': companions,
        })
    
    def _create_event_registrations(self):
        """Create event registrations for this guest and companions when RSVP is accepted"""
        self.ensure_one()
        
        # Only create if RSVP is accepted
        if self.rsvp_status != 'accepted':
            return self.env['event.registration']
        
        # Find the related event.event from calendar_event_id
        if not self.calendar_event_id:
            return self.env['event.registration']
        
        event = self.env['event.event'].search([
            ('calendar_event_id', '=', self.calendar_event_id.id)
        ], limit=1)
        
        if not event:
            return self.env['event.registration']
        
        # Format phone number for registration
        formatted_phone = False
        if self.phone_number:
            # Clean phone number (remove non-digits)
            formatted_phone = ''.join(filter(str.isdigit, self.phone_number))
            if not formatted_phone:
                formatted_phone = self.phone_number
        
        # Get existing registrations for this guest
        existing_registrations = self.event_registration_ids.filtered(lambda r: r.state != 'cancel')
        
        # Update existing main guest registration with current name and phone if it exists
        if existing_registrations:
            main_registration = existing_registrations[0]  # First one is the main guest
            update_vals = {}
            if main_registration.name != (self.name or 'Guest'):
                update_vals['name'] = self.name or 'Guest'
            if formatted_phone and main_registration.phone != formatted_phone:
                update_vals['phone'] = formatted_phone
            if self.email and main_registration.email != self.email:
                update_vals['email'] = self.email
            if update_vals:
                main_registration.write(update_vals)
        
        # Calculate how many registrations we need (1 for guest + companions_count)
        total_needed = 1 + self.companions_count
        existing_count = len(existing_registrations)
        
        # Get or create partner for the guest
        partner = False
        if self.email or self.phone_number:
            # Try to find existing partner
            partner_domain = []
            if self.email:
                partner_domain.append(('email', '=', self.email))
            if self.phone_number:
                cleaned_phone = ''.join(filter(str.isdigit, self.phone_number))
                if cleaned_phone:
                    partner_domain.append('|')
                    partner_domain.append(('phone', '=', cleaned_phone))
                    partner_domain.append(('mobile', '=', cleaned_phone))
            
            if partner_domain:
                partner = self.env['res.partner'].search(partner_domain, limit=1)
            
            # Create partner if not found
            if not partner:
                partner_vals = {
                    'name': self.name or 'Guest',
                    'email': self.email or False,
                }
                if self.phone_number:
                    cleaned_phone = ''.join(filter(str.isdigit, self.phone_number))
                    partner_vals['phone'] = cleaned_phone or self.phone_number
                partner = self.env['res.partner'].create(partner_vals)
        
        created_registrations = self.env['event.registration']
        
        # If no existing registrations, create all needed
        if existing_count == 0:
            # Create registration for the main guest
            registration_vals = {
                'event_id': event.id,
                'name': self.name or 'Guest',
                'email': self.email or False,
                'phone': formatted_phone or False,
                'partner_id': partner.id if partner else False,
                'guest_id': self.id,
                'state': 'open',
            }
            main_registration = self.env['event.registration'].create(registration_vals)
            created_registrations |= main_registration
            
            # Create registrations for companions
            for i in range(1, self.companions_count + 1):
                companion_vals = {
                    'event_id': event.id,
                    'name': f"{self.name} - Companion {i}",
                    'email': False,
                    'phone': False,
                    'partner_id': partner.id if partner else False,
                    'guest_id': self.id,
                    'state': 'open',
                }
                companion_reg = self.env['event.registration'].create(companion_vals)
                created_registrations |= companion_reg
        elif existing_count < total_needed:
            # Need to create more registrations (companions increased)
            # The first registration should be the main guest (already exists)
            # Create additional companion registrations
            # Calculate how many companions we already have (existing_count - 1 for main guest)
            existing_companions = max(0, existing_count - 1)
            for i in range(existing_companions + 1, self.companions_count + 1):
                companion_vals = {
                    'event_id': event.id,
                    'name': f"{self.name} - Companion {i}",
                    'email': False,
                    'phone': False,
                    'partner_id': partner.id if partner else False,
                    'guest_id': self.id,
                    'state': 'open',
                }
                companion_reg = self.env['event.registration'].create(companion_vals)
                created_registrations |= companion_reg
        elif existing_count > total_needed:
            # Too many registrations (companions decreased), cancel the extra ones
            extra_registrations = existing_registrations[total_needed:]
            extra_registrations.write({'state': 'cancel'})
        
        return created_registrations
    
    def _cancel_event_registrations(self):
        """Cancel event registrations when RSVP status changes from accepted"""
        self.ensure_one()
        
        if self.event_registration_ids:
            # Cancel all registrations linked to this guest
            self.event_registration_ids.write({'state': 'cancel'})
    
    def _send_barcode_via_whatsapp(self):
        """Send barcode image to guest via WhatsApp automatically"""
        self.ensure_one()
        
        # Get the first active registration (main guest)
        registration = self.event_registration_ids.filtered(
            lambda r: r.state != 'cancel'
        )[:1]
        
        if not registration:
            _logger.warning(f'No active registration found for guest {self.name} to send barcode')
            return False
        
        # Check if barcode image exists
        if not registration.barcode_image:
            _logger.warning(f'No barcode image found for registration {registration.name}')
            return False
        
        # Get WhatsApp server URL
        server_url = self.env['ir.config_parameter'].sudo().get_param(
            'whatsapp_wedding_invitations.server_url',
            'http://localhost:3000'
        )
        
        # Format phone number
        phone = self._format_phone_number()
        if not phone:
            _logger.warning(f'No valid phone number for guest {self.name}')
            return False
        
        # Prepare message
        event_name = self.event_id.name if self.event_id else 'Event'
        message = f"""✅ *تم تأكيد حضورك!*

مرحباً *{self.name}*

تم تأكيد حضورك في *{event_name}* بنجاح! 🎉

📋 *بطاقة الدخول الخاصة بك:*
استخدم الباركود المرفق للدخول إلى الحدث.

نشكرك على تأكيد حضورك وننتظر رؤيتك! 🎊"""
        
        try:
            # Get barcode image data - use same method as WhatsApp attachment wizard
            barcode_data = registration.barcode_image
            file_data = None
            
            # Handle different data types (same as whatsapp_attachment_wizard.py)
            if isinstance(barcode_data, bytes):
                # barcode_data is bytes - likely UTF-8 encoded base64 string, NOT raw binary
                try:
                    media_base64 = barcode_data.decode('utf-8')
                    file_data = base64.b64decode(media_base64, validate=True)
                    _logger.info(f'Barcode data was bytes (UTF-8 base64 string), decoded successfully (length: {len(file_data)} bytes)')
                except (UnicodeDecodeError, ValueError) as e:
                    # If UTF-8 decode fails, it might be raw binary data
                    _logger.warning(f'Could not decode as UTF-8, treating as raw binary: {str(e)}')
                    media_base64 = base64.b64encode(barcode_data).decode('utf-8')
                    file_data = barcode_data
            elif isinstance(barcode_data, str):
                # If it's already a string, it should be base64
                media_base64 = barcode_data
                # Remove data URL prefix if present
                if media_base64.startswith('data:'):
                    media_base64 = media_base64.split(',', 1)[1] if ',' in media_base64 else media_base64
                    _logger.info('Removed data URL prefix from barcode data')
                
                # Clean base64 string (remove whitespace, newlines, etc.)
                media_base64 = media_base64.strip().replace('\n', '').replace('\r', '').replace(' ', '')
                
                # Validate base64 string format
                try:
                    # Try to decode to verify it's valid base64
                    file_data = base64.b64decode(media_base64, validate=True)
                    
                    # Verify decoded data is not empty
                    if len(file_data) == 0:
                        raise ValueError('Decoded base64 data is empty')
                    
                    # For PNG images, verify file header
                    header = file_data[:4]
                    if header[:4] != b'\x89PNG':
                        _logger.warning(f'PNG header mismatch: got {header.hex()}, expected 89504E47')
                    else:
                        _logger.info(f'Barcode data is valid PNG image (decoded length: {len(file_data)} bytes)')
                except Exception as decode_error:
                    _logger.error(f'Invalid base64 data: {str(decode_error)}')
                    raise ValueError(f'Invalid base64 data in barcode image: {str(decode_error)}')
            else:
                # Try to convert to string (shouldn't happen, but just in case)
                _logger.warning(f'Unexpected barcode data type: {type(barcode_data)}, converting to string')
                media_base64 = str(barcode_data)
                try:
                    file_data = base64.b64decode(media_base64, validate=True)
                except Exception:
                    raise ValueError(f'Cannot decode barcode data as base64')
            
            # Check file size (WhatsApp limit is usually 16MB, but we'll use 10MB to be safe)
            file_size = len(file_data)
            file_size_mb = file_size / (1024 * 1024)
            
            if file_size_mb > 10:
                raise ValueError(f'Barcode image is too large ({file_size_mb:.2f} MB). Maximum size is 10 MB.')
            
            _logger.info(f'Preparing to send barcode image: size: {file_size_mb:.2f} MB, mimetype: image/png')
            
            # Verify base64 string before sending
            if not media_base64 or len(media_base64) < 100:
                raise ValueError(f'Invalid base64 string: too short or empty (length: {len(media_base64) if media_base64 else 0})')
            
            # Log first few characters for debugging (but not the whole string)
            _logger.info(f'Base64 string length: {len(media_base64)}, first 50 chars: {media_base64[:50]}...')
            
            # Verify decoded data one more time before sending
            try:
                test_decode = base64.b64decode(media_base64, validate=True)
                if len(test_decode) != len(file_data):
                    _logger.warning(f'Base64 decode mismatch: test decode={len(test_decode)}, original={len(file_data)}')
            except Exception as e:
                _logger.error(f'Base64 validation failed before sending: {str(e)}')
                raise ValueError(f'Base64 validation failed: {str(e)}')
            
            # Send via WhatsApp
            send_url = f'{server_url}/api/send-media'
            payload = {
                'phoneNumber': phone,
                'message': message,
                'mediaBase64': media_base64,  # Base64 string
                'mediaMimetype': 'image/png',
                'mediaFilename': f'barcode_{registration.barcode or registration.name}.png'
            }
            
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                send_url,
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=60) as response:
                response_data = json.loads(response.read().decode())
                if response_data.get('success'):
                    _logger.info(f'✅ Barcode image sent successfully to {self.name} ({phone})')
                    return True
                else:
                    _logger.error(f'❌ Failed to send barcode image to {self.name}: {response_data.get("error")}')
                    return False
                    
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if hasattr(e, 'read') else str(e)
            _logger.error(f'HTTP error sending barcode image: {e.code} - {error_body}', exc_info=True)
            return False
        except Exception as e:
            _logger.error(f'Error sending barcode image to {self.name}: {str(e)}', exc_info=True)
            return False
    
    def write(self, vals):
        """Override write to auto-create event registrations when RSVP changes to accepted"""
        # Track RSVP status change and companions count change
        rsvp_changed = 'rsvp_status' in vals
        companions_changed = 'companions_count' in vals
        old_rsvp_status = {}
        old_companions_count = {}
        
        if rsvp_changed:
            # Store old RSVP status for each record
            for record in self:
                old_rsvp_status[record.id] = record.rsvp_status
        
        if companions_changed:
            # Store old companions count for each record
            for record in self:
                old_companions_count[record.id] = record.companions_count
        
        # Call super to perform the write
        result = super(EventGuest, self).write(vals)
        
        # After write, check if we need to create or cancel registrations
        # Skip if called from webhook context to avoid concurrency issues
        if self.env.context.get('skip_event_registration'):
            return result
            
        for guest in self:
            if rsvp_changed:
                old_status = old_rsvp_status.get(guest.id)
                new_status = guest.rsvp_status
                
                # If changing to accepted, create registrations
                if new_status == 'accepted' and old_status != 'accepted':
                    try:
                        registrations = guest._create_event_registrations()
                        # Send barcode image via WhatsApp after creating registrations
                        # Only send if auto_reply_count < 4 (to allow up to 4 auto-replies)
                        # Note: auto_reply_count is incremented in process_whatsapp_response, not here
                        # This is to avoid double incrementing when called from process_whatsapp_response
                        if registrations and guest.auto_reply_count < 4 and not self.env.context.get('from_whatsapp_response'):
                            # Refresh to ensure computed fields are loaded
                            registrations.invalidate_recordset(['barcode', 'barcode_image'])
                            # Force recompute barcode_image
                            for reg in registrations:
                                if reg.barcode:
                                    reg._compute_barcode_image()
                            # Send barcode image
                            guest._send_barcode_via_whatsapp()
                            # Increment auto_reply_count only if not called from process_whatsapp_response
                            guest.auto_reply_count += 1
                            _logger.info(f'📊 Guest {guest.name} auto_reply_count incremented to {guest.auto_reply_count} (from write method)')
                    except Exception as e:
                        _logger.warning(f'Failed to create event registration for guest {guest.name}: {e}')
                # If changing from accepted to something else, cancel registrations
                elif old_status == 'accepted' and new_status != 'accepted':
                    try:
                        guest._cancel_event_registrations()
                    except Exception as e:
                        import logging
                        _logger = logging.getLogger(__name__)
                        _logger.warning(f'Failed to cancel event registration for guest {guest.name}: {e}')
            elif companions_changed and guest.rsvp_status == 'accepted':
                # If companions count changed and RSVP is already accepted, update registrations
                old_count = old_companions_count.get(guest.id, 0)
                new_count = guest.companions_count
                if old_count != new_count:
                    try:
                        guest._create_event_registrations()
                    except Exception as e:
                        import logging
                        _logger = logging.getLogger(__name__)
                        _logger.warning(f'Failed to update event registration for guest {guest.name}: {e}')
        
        return result
    
    def action_decline_attendance(self, method='manual', message=None, skip_registration=False):
        """Mark guest as declined"""
        ctx = {'skip_event_registration': skip_registration} if skip_registration else {}
        self.with_context(**ctx).write({
            'rsvp_status': 'declined',
            'rsvp_response_date': fields.Datetime.now(),
            'rsvp_response_method': method,
            'rsvp_message': message,
            'companions_count': 0,
        })
    
    def action_reset_rsvp(self):
        """Reset RSVP status to pending"""
        self.write({
            'rsvp_status': 'pending',
            'rsvp_response_date': False,
            'rsvp_response_method': False,
            'rsvp_message': False,
            'companions_count': 0,
        })
    
    @api.model
    def find_by_phone(self, phone_number):
        """Find guest by phone number - matches by comparing cleaned (digits-only) phone numbers"""
        import logging
        _logger = logging.getLogger(__name__)
        
        # Clean incoming phone number
        # Also remove @lid suffix if present (WhatsApp Business API format)
        phone_cleaned = phone_number.split('@')[0] if '@' in phone_number else phone_number
        
        # Remove + and 00 prefixes before cleaning digits (to preserve them for normalization)
        # But first, let's clean digits to get base number
        cleaned = ''.join(filter(str.isdigit, phone_cleaned))
        _logger.info(f'🔍 Finding guest by phone: original={phone_number}, after_@_removal={phone_cleaned}, cleaned={cleaned}')
        
        if not cleaned:
            _logger.warning(f'❌ Phone number is empty after cleaning')
            return self.browse()
        
        # Get all guests and compare cleaned phone numbers
        all_guests = self.search([('phone_number', '!=', False)])
        matching_guests = self.browse()
        
        # Prepare search patterns - try multiple variations for international numbers
        # For numbers like +966592155935, we want to match:
        # - 966592155935 (with country code)
        # - 0592155935 (local format)
        # - 592155935 (without leading zero)
        # - Last 9 digits: 92155935
        
        # Remove leading country codes if present (common patterns)
        # Saudi: 966, Egypt: 20, UAE: 971, etc.
        # Also handle 00 prefix (international dialing code)
        cleaned_normalized = cleaned
        # Remove 00 prefix if present (international dialing code)
        if cleaned.startswith('00'):
            cleaned_normalized = cleaned[2:]
        
        # Now remove country codes
        if cleaned_normalized.startswith('966'):  # Saudi Arabia
            cleaned_normalized = cleaned_normalized[3:]  # Remove 966
        elif cleaned_normalized.startswith('20'):  # Egypt
            cleaned_normalized = cleaned_normalized[2:]  # Remove 20
        elif cleaned_normalized.startswith('971'):  # UAE
            cleaned_normalized = cleaned_normalized[3:]  # Remove 971
        
        # Prepare search patterns
        last10 = cleaned[-10:] if len(cleaned) >= 10 else cleaned
        last9 = cleaned[-9:] if len(cleaned) >= 9 else cleaned
        last8 = cleaned[-8:] if len(cleaned) >= 8 else cleaned
        
        # For normalized (without country code)
        normalized_last9 = cleaned_normalized[-9:] if len(cleaned_normalized) >= 9 else cleaned_normalized
        normalized_last8 = cleaned_normalized[-8:] if len(cleaned_normalized) >= 8 else cleaned_normalized
        
        _logger.info(f'📋 Total guests with phone: {len(all_guests)}, searching for: {cleaned} (normalized: {cleaned_normalized}, last10={last10}, last9={last9}, last8={last8})')
        
        for guest in all_guests:
            # Clean the guest's phone number
            guest_cleaned = ''.join(filter(str.isdigit, guest.phone_number or ''))
            if not guest_cleaned:
                continue
            
            # Normalize guest phone (remove country code if present)
            # Also handle 00 prefix (international dialing code)
            guest_normalized = guest_cleaned
            # Remove 00 prefix if present
            if guest_cleaned.startswith('00'):
                guest_normalized = guest_cleaned[2:]
            elif guest_cleaned.startswith('+'):
                guest_normalized = guest_cleaned[1:]
            
            # Now remove country codes
            if guest_normalized.startswith('966'):
                guest_normalized = guest_normalized[3:]
            elif guest_normalized.startswith('20'):
                guest_normalized = guest_normalized[2:]
            elif guest_normalized.startswith('971'):
                guest_normalized = guest_normalized[3:]
            
            # Check for matches:
            # 1. Exact match (with or without country code)
            # 2. Normalized match (without country code)
            # 3. Last 10 digits match
            # 4. Last 9 digits match
            # 5. Last 8 digits match (for local numbers)
            guest_last10 = guest_cleaned[-10:] if len(guest_cleaned) >= 10 else guest_cleaned
            guest_last9 = guest_cleaned[-9:] if len(guest_cleaned) >= 9 else guest_cleaned
            guest_last8 = guest_cleaned[-8:] if len(guest_cleaned) >= 8 else guest_cleaned
            guest_normalized_last9 = guest_normalized[-9:] if len(guest_normalized) >= 9 else guest_normalized
            guest_normalized_last8 = guest_normalized[-8:] if len(guest_normalized) >= 8 else guest_normalized
            
            # Log first few guests for debugging
            if len(matching_guests) == 0 and len(all_guests) <= 20:
                _logger.info(f'  Checking: {guest.name}, original_phone: {guest.phone_number}, cleaned: {guest_cleaned}, normalized: {guest_normalized}, last9: {guest_last9}, last8: {guest_last8}')
            
            # Multiple matching strategies
            match_found = False
            match_reason = None
            
            if cleaned == guest_cleaned:
                match_found = True
                match_reason = 'Exact match'
            elif cleaned_normalized == guest_normalized:
                match_found = True
                match_reason = 'Normalized match'
            elif cleaned == guest_normalized:
                match_found = True
                match_reason = 'Incoming with country code matches guest without'
            elif cleaned_normalized == guest_cleaned:
                match_found = True
                match_reason = 'Incoming without country code matches guest with'
            elif last10 == guest_last10:
                match_found = True
                match_reason = 'Last 10 digits match'
            elif last9 == guest_last9:
                match_found = True
                match_reason = 'Last 9 digits match'
            elif last8 == guest_last8:
                match_found = True
                match_reason = 'Last 8 digits match'
            elif normalized_last9 == guest_normalized_last9:
                match_found = True
                match_reason = 'Normalized last 9 match'
            elif normalized_last8 == guest_normalized_last8:
                match_found = True
                match_reason = 'Normalized last 8 match'
            elif cleaned.endswith(guest_last10):
                match_found = True
                match_reason = 'Incoming ends with guest last 10'
            elif guest_cleaned.endswith(last10):
                match_found = True
                match_reason = 'Guest ends with incoming last 10'
            elif cleaned.endswith(guest_last9):
                match_found = True
                match_reason = 'Incoming ends with guest last 9'
            elif guest_cleaned.endswith(last9):
                match_found = True
                match_reason = 'Guest ends with incoming last 9'
            elif cleaned_normalized.endswith(guest_normalized_last9):
                match_found = True
                match_reason = 'Normalized incoming ends with guest normalized last 9'
            elif guest_normalized.endswith(normalized_last9):
                match_found = True
                match_reason = 'Guest normalized ends with incoming normalized last 9'
            
            if match_found:
                _logger.info(f'  ✅ Match found: {guest.name}, phone: {guest.phone_number}, cleaned: {guest_cleaned}, normalized: {guest_normalized}, reason: {match_reason}')
                matching_guests |= guest
        
        _logger.info(f'✅ Found {len(matching_guests)} guests: {matching_guests.mapped("name") if matching_guests else "None"}')
        return matching_guests
    
    @api.model
    def find_by_token(self, token):
        """Find guest by confirmation token"""
        if not token:
            return self.browse()
        return self.search([('confirmation_token', '=', token)], limit=1)
    
    @api.model
    def find_by_name(self, name):
        """Find guests by name (case-insensitive, partial match)
        
        This is used as a fallback when phone number lookup fails
        (e.g., when WhatsApp sends LID instead of actual phone number)
        """
        import logging
        _logger = logging.getLogger(__name__)
        
        if not name:
            return self.browse()
        
        name = name.strip()
        _logger.info(f'🔍 Finding guest by name: "{name}"')
        
        # Search for exact match first (case-insensitive)
        guests = self.search([('name', '=ilike', name)])
        if guests:
            _logger.info(f'✅ Found {len(guests)} guest(s) by exact name match: {guests.mapped("name")}')
            return guests
        
        # Try partial match (name contains search term)
        guests = self.search([('name', 'ilike', name)])
        if guests:
            _logger.info(f'✅ Found {len(guests)} guest(s) by partial name match: {guests.mapped("name")}')
            return guests
        
        # Try searching with each word in the name
        name_parts = name.split()
        if len(name_parts) > 1:
            for part in name_parts:
                if len(part) >= 2:  # Skip very short words
                    guests = self.search([('name', 'ilike', part)])
                    if guests:
                        _logger.info(f'✅ Found {len(guests)} guest(s) by name part "{part}": {guests.mapped("name")}')
                        return guests
        
        _logger.warning(f'⚠️ No guests found for name: "{name}"')
        return self.browse()
    
    @api.model
    def extract_phone_from_sender_name(self, sender_name):
        """Extract phone number from senderName if it looks like a phone number.
        
        WhatsApp sometimes sends senderName as the phone number format:
        - "+966 56 599 6541" -> "966565996541"
        - "+20 111 110 6797" -> "201111106797"
        
        Returns cleaned phone number or None if not a phone number format
        """
        if not sender_name:
            return None
        
        # Check if senderName looks like a phone number (starts with + or contains digits)
        # and has at least 8 digits
        cleaned = ''.join(filter(str.isdigit, sender_name))
        if len(cleaned) >= 8:
            _logger.info(f'📞 Extracted phone from senderName: "{sender_name}" -> "{cleaned}"')
            return cleaned
        return None
    
    @api.model
    def is_whatsapp_lid(self, phone_number):
        """Check if a number looks like a WhatsApp LID (Linked ID) rather than a real phone number.
        
        WhatsApp LIDs are typically:
        - Very long (> 12 digits)
        - Don't start with common country codes
        - Often end with @lid
        """
        if not phone_number:
            return False
        
        # Remove @lid suffix if present
        cleaned = phone_number.split('@')[0]
        digits = ''.join(filter(str.isdigit, cleaned))
        
        # LIDs are usually very long (>12 digits) and don't look like real phone numbers
        if len(digits) > 12:
            # Check if it doesn't start with common country codes
            common_prefixes = ['966', '20', '971', '968', '962', '963', '964', '965', '967', '1', '44', '49', '33']
            if not any(digits.startswith(prefix) for prefix in common_prefixes):
                return True
        
        return False
    
    @api.model
    def process_whatsapp_response(self, phone_number, message, sender_name=''):
        """Process incoming WhatsApp message and update RSVP status
        
        Auto-reply can be sent up to 4 times when guest sends نعم
        After 4 times, no more auto-replies are sent to that guest.
        
        Args:
            phone_number: Phone number or WhatsApp ID of the sender
            message: Message content
            sender_name: Optional sender name for fallback search when phone number is WhatsApp ID
        """
        import logging
        _logger = logging.getLogger(__name__)
        
        _logger.info(f'🔍 Processing WhatsApp response - Phone: {phone_number}, Message: "{message}", Sender Name: "{sender_name}"')
        
        # Check if phone_number looks like a WhatsApp LID
        if self.is_whatsapp_lid(phone_number):
            _logger.info(f'⚠️ Phone number looks like a WhatsApp LID: {phone_number}')
            # Try to extract actual phone from senderName
            extracted_phone = self.extract_phone_from_sender_name(sender_name)
            if extracted_phone:
                _logger.info(f'📞 Using extracted phone from senderName: {extracted_phone}')
                phone_number = extracted_phone
        
        # First try to find by phone number
        guests = self.find_by_phone(phone_number)
        
        # If not found and sender_name looks like a phone number, try that
        if not guests and sender_name:
            extracted_phone = self.extract_phone_from_sender_name(sender_name)
            if extracted_phone and extracted_phone != phone_number:
                _logger.info(f'🔍 Trying extracted phone from senderName: {extracted_phone}')
                guests = self.find_by_phone(extracted_phone)
                if guests:
                    _logger.info(f'✅ Found {len(guests)} guest(s) by extracted phone from senderName')
        
        # If still not found and sender_name is a name (not phone), try to find by name
        if not guests and sender_name:
            # Check if senderName doesn't look like a phone number
            sender_digits = ''.join(filter(str.isdigit, sender_name))
            if len(sender_digits) < 8:  # Not a phone number, try as name
                _logger.info(f'🔍 Phone lookup failed, trying to find by sender name: "{sender_name}"')
                guests = self.find_by_name(sender_name)
                if guests:
                    _logger.info(f'✅ Found {len(guests)} guest(s) by name: {guests.mapped("name")}')
        
        if not guests:
            _logger.warning(f'⚠️ No guests found for phone: {phone_number} or name: "{sender_name}"')
            return {'success': False, 'error': 'Guest not found', 'phone_number': phone_number, 'sender_name': sender_name}
        
        # Parse the message first to determine response type
        # ONLY exact "نعم" or "لا" trigger auto-reply - no other words allowed
        message_cleaned = message.strip()
        
        # Check for EXACT match only (no other words)
        is_positive = message_cleaned == 'نعم'
        is_negative = message_cleaned == 'لا'
        
        _logger.info(f'🔍 Message analysis - Original: "{message}", Cleaned: "{message_cleaned}", is_positive: {is_positive}, is_negative: {is_negative}')
        
        # Separate guests who already responded from those who haven't
        pending_guests = guests.filtered(lambda g: g.rsvp_status == 'pending')
        responded_guests = guests.filtered(lambda g: g.rsvp_status != 'pending')
        
        if responded_guests:
            _logger.info(f'📝 Guests who already responded: {responded_guests.mapped("name")} (status: {responded_guests.mapped("rsvp_status")})')
        
        # For positive responses (نعم), allow auto-reply up to 8 times
        # Filter guests who can still receive auto-reply (auto_reply_count < 8)
        # This applies even if rsvp_status != 'pending' (e.g., already accepted)
        if is_positive:
            guests_to_process = guests.filtered(lambda g: g.auto_reply_count < 8)
            guests_to_skip = guests.filtered(lambda g: g.auto_reply_count >= 8)
            
            if guests_to_skip:
                _logger.info(f'📝 Guests who reached auto-reply limit (8 times): {guests_to_skip.mapped("name")} (count: {guests_to_skip.mapped("auto_reply_count")})')
            
            if not guests_to_process:
                _logger.info(f'📝 All guests reached auto-reply limit (8 times). No auto-reply.')
                _logger.info(f'📊 Summary - All guests: {guests.mapped("name")}, Auto-reply counts: {guests.mapped("auto_reply_count")}')
                return {
                    'success': True,
                    'status': 'auto_reply_limit_reached',
                    'skip_auto_reply': True,
                    'guests': guests.mapped('name'),
                    'auto_reply_counts': {g.name: g.auto_reply_count for g in guests}
                }
            
            # Process guests who can still receive auto-reply
            # This includes guests who already responded (rsvp_status != 'pending')
            _logger.info(f'📝 Processing response for guests (auto_reply_count < 8): {guests_to_process.mapped("name")} (count: {guests_to_process.mapped("auto_reply_count")}, statuses: {guests_to_process.mapped("rsvp_status")})')
            guests = guests_to_process
        else:
            # For negative responses or unrecognized messages, only process pending guests
            if not pending_guests:
                _logger.info(f'📝 All guests already responded. No auto-reply.')
                _logger.info(f'📊 Summary - All guests: {guests.mapped("name")}, Statuses: {guests.mapped("rsvp_status")}, Auto-reply counts: {guests.mapped("auto_reply_count")}')
                return {
                    'success': True,
                    'status': 'already_responded',
                    'skip_auto_reply': True,
                    'guests': guests.mapped('name'),
                    'auto_reply_counts': {g.name: g.auto_reply_count for g in guests}
                }
            
            # Process only pending guests
            _logger.info(f'📝 Processing response for pending guests: {pending_guests.mapped("name")}')
            guests = pending_guests
        
        # Determine response type
        response_type = None
        if is_positive:
            response_type = 'accepted'
            _logger.info(f'✅ Recognized POSITIVE response (نعم/yes) from {guests.mapped("name")} (phone: {phone_number})')
        elif is_negative:
            response_type = 'declined'
            _logger.info(f'❌ Recognized NEGATIVE response (لا/no) from {guests.mapped("name")} (phone: {phone_number})')
        else:
            _logger.info(f'❓ Unrecognized message from {guests.mapped("name")} (phone: {phone_number}): "{message}"')
        
        if response_type:
            # Process response and send auto-reply (up to 8 times for positive responses)
            for guest in guests:
                if response_type == 'accepted':
                    _logger.info(f'📝 Processing ACCEPTED response for guest: {guest.name} (auto_reply_count: {guest.auto_reply_count})')
                    
                    # Only update RSVP status if guest is still pending
                    if guest.rsvp_status == 'pending':
                        # Don't skip registration - we need to create registrations and send barcode
                        # Pass context to prevent double incrementing auto_reply_count in write()
                        guest.with_context(from_whatsapp_response=True).action_confirm_attendance(method='whatsapp', message=message, skip_registration=False)
                        _logger.info(f'✅ Guest {guest.name} attendance confirmed. Registrations created.')
                    else:
                        _logger.info(f'📝 Guest {guest.name} already has status "{guest.rsvp_status}". Skipping status update.')
                    
                    # Send barcode image after creating registrations (if needed)
                    # The _send_barcode_via_whatsapp will be called automatically in write() method
                    # But we also call it here to ensure it's sent immediately
                    try:
                        # Wait a bit for barcode image to be computed
                        time.sleep(2)
                        # Refresh guest to get new registrations
                        guest.invalidate_recordset(['event_registration_ids'])
                        # The barcode should be sent automatically in write() method
                        # But if it wasn't sent, try to send it here
                        if guest.event_registration_ids:
                            _logger.info(f'📤 Attempting to send barcode image to {guest.name}...')
                            barcode_sent = guest._send_barcode_via_whatsapp()
                            if barcode_sent:
                                _logger.info(f'✅ Barcode image sent successfully to {guest.name}')
                            else:
                                _logger.warning(f'⚠️ Barcode image sending returned False for {guest.name}')
                    except Exception as e:
                        _logger.error(f'❌ Failed to send barcode image to {guest.name}: {e}', exc_info=True)
                    
                    # Increment auto_reply_count for positive responses
                    guest.auto_reply_count += 1
                    _logger.info(f'📊 Guest {guest.name} auto_reply_count incremented to {guest.auto_reply_count}')
                else:
                    # For negative responses, only update if pending
                    if guest.rsvp_status == 'pending':
                        guest.action_decline_attendance(method='whatsapp', message=message, skip_registration=False)
            
            _logger.info(f'✅ Response from {guests.mapped("name")}: {response_type}. Auto-reply text message will be sent.')
            _logger.info(f'📊 Summary - Guests processed: {len(guests)}, Names: {guests.mapped("name")}, Auto-reply counts: {guests.mapped("auto_reply_count")}')
            return {
                'success': True,
                'status': response_type,
                'skip_auto_reply': False,  # Send auto-reply
                'guests': guests.mapped('name'),
                'auto_reply_counts': {g.name: g.auto_reply_count for g in guests}
            }
        
        # Message not understood and guest hasn't responded yet
        # Don't send auto-reply for unrecognized messages from pending guests either
        _logger.info(f'❓ Unrecognized message from pending guest. No auto-reply.')
        return {
            'success': False,
            'error': 'Could not understand response',
            'skip_auto_reply': True,  # Don't spam with "I didn't understand" messages
            'message': message
        }





