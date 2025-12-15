# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import urllib.request
import urllib.error
import json
import logging
import time
import random
import base64
import mimetypes
import io

_logger = logging.getLogger(__name__)

# Try to import PIL for image compression
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    _logger.warning('PIL/Pillow not available. Image compression will be disabled.')


class WhatsAppInvitationWizard(models.TransientModel):
    _name = 'whatsapp.invitation.wizard'
    _description = 'WhatsApp Invitation Wizard'

    event_id = fields.Many2one(
        'calendar.event',
        string='Event',
        required=True,
        readonly=True
    )
    
    guest_ids = fields.Many2many(
        'event.guest',
        'whatsapp_invitation_guest_rel',
        'wizard_id',
        'guest_id',
        string='Guests',
        required=True,
        help='Select guests to send invitations to'
    )
    
    message_template = fields.Text(
        string='Message Template',
        required=True,
        help='Message template for invitations. Use {name} for guest name, {event_name} for event name, {date} for event date, {venue} for venue, {time} for time.'
    )
    
    invitation_image = fields.Binary(
        string='Invitation Image',
        attachment=True,
        help='Image to send with the invitation message (optional). Supported formats: JPG, PNG, GIF.'
    )
    
    invitation_image_filename = fields.Char(
        string='Image Filename',
        help='Filename of the invitation image'
    )
    
    send_with_image = fields.Boolean(
        string='Send with Image',
        compute='_compute_send_with_image',
        store=False,
        help='Whether to send the invitation with an image'
    )
    
    send_mode = fields.Selection([
        ('text_only', 'Text Only (with image URL in message)'),
        ('with_image', 'With Image Attachment'),
    ], string='Send Mode', default='with_image',
       help='Choose how to send the invitation. "With Image Attachment" sends the actual image file to WhatsApp.'
    )
    
    send_progress = fields.Text(
        string='Progress',
        readonly=True,
        help='Progress of sending invitations'
    )
    
    @api.depends('invitation_image')
    def _compute_send_with_image(self):
        for record in self:
            record.send_with_image = bool(record.invitation_image)
    
    @api.model
    def default_get(self, fields_list):
        """Set default values from context"""
        res = super(WhatsAppInvitationWizard, self).default_get(fields_list)
        
        if 'event_id' in fields_list and 'default_event_id' in self._context:
            res['event_id'] = self._context['default_event_id']
        
        if 'guest_ids' in fields_list:
            default_guests = self._context.get('default_guest_ids')
            if default_guests:
                res['guest_ids'] = self._format_guest_defaults(default_guests)
        
        if 'message_template' in fields_list and 'default_message_template' in self._context:
            res['message_template'] = self._context['default_message_template']
        elif 'message_template' in fields_list and res.get('event_id'):
            event = self.env['calendar.event'].browse(res['event_id'])
            res['message_template'] = event.invitation_message_template or event._default_invitation_template()
        
        # Get invitation image from event
        if 'invitation_image' in fields_list:
            if 'default_invitation_image' in self._context:
                res['invitation_image'] = self._context['default_invitation_image']
            elif res.get('event_id'):
                # Fallback: read from event if not in context
                event = self.env['calendar.event'].browse(res['event_id'])
                if event.invitation_image:
                    res['invitation_image'] = event.invitation_image
        
        if 'invitation_image_filename' in fields_list:
            if 'default_invitation_image_filename' in self._context:
                res['invitation_image_filename'] = self._context['default_invitation_image_filename']
            elif res.get('event_id'):
                # Fallback: read from event if not in context
                event = self.env['calendar.event'].browse(res['event_id'])
                if event.invitation_image_filename:
                    res['invitation_image_filename'] = event.invitation_image_filename
        
        # Auto-set send_mode to 'with_image' if image is available
        if 'send_mode' in fields_list and res.get('invitation_image'):
            res['send_mode'] = 'with_image'
        
        return res

    def _format_guest_defaults(self, value):
        """Normalize default guest values to proper command format."""
        if isinstance(value, (list, tuple)):
            # Already a command list?
            if value and isinstance(value[0], (list, tuple)):
                first = value[0]
                if len(first) >= 3 and isinstance(first[0], int):
                    return [tuple(cmd) for cmd in value]
            return [(6, 0, list(value))]
        return [(6, 0, [value])]
    
    def _get_server_url(self):
        """Get WhatsApp server URL from settings"""
        return self.env['ir.config_parameter'].sudo().get_param(
            'whatsapp_wedding_invitations.server_url',
            'http://localhost:3000'
        )
    
    def _get_delay(self):
        """Get random delay between messages (2000-3500ms) to appear more human-like"""
        min_delay = int(self.env['ir.config_parameter'].sudo().get_param(
            'whatsapp_wedding_invitations.delay_between_messages',
            '2000'
        ))
        max_delay = min_delay + 1500  # Add up to 1.5 seconds randomly
        return random.randint(min_delay, max_delay)
    
    def _prepare_guest_data(self, guest):
        """Prepare guest data for API"""
        return {
            'name': guest.name,
            'phoneNumber': guest._format_phone_number(),
            'guestName': guest.name.split()[0] if guest.name else guest.name
        }
    
    def _personalize_message(self, guest):
        """Personalize message template for guest"""
        event = self.event_id
        message = self.message_template
        
        # Get image URL and ensure it has proper protocol
        image_url = event._get_invitation_image_url() if hasattr(event, '_get_invitation_image_url') else ''
        if image_url and not image_url.startswith('http'):
            image_url = 'https://' + image_url
        
        # Get RSVP URLs if guest has them
        confirm_url = guest.get_confirmation_url() if hasattr(guest, 'get_confirmation_url') else ''
        decline_url = guest.get_decline_url() if hasattr(guest, 'get_decline_url') else ''
        
        # Replace placeholders
        replacements = {
            '{name}': guest.name or '',
            '{guestName}': guest.name.split()[0] if guest.name else guest.name or '',
            '{event_name}': event.name or 'Event',
            '{date}': event._format_event_date(),
            '{venue}': event._get_venue(),
            '{time}': event._format_event_time(),
            '{organizer}': event.user_id.name if event.user_id else 'Organizer',
            '{image_url}': image_url,
            '{confirm_url}': confirm_url,
            '{decline_url}': decline_url,
        }
        
        for placeholder, value in replacements.items():
            message = message.replace(placeholder, value)
        
        # Clean up empty URL placeholders (remove lines with empty URLs)
        if not image_url:
            lines = message.split('\n')
            lines = [line for line in lines if '{image_url}' not in line and line.strip()]
            message = '\n'.join(lines)
        
        if not confirm_url:
            lines = message.split('\n')
            lines = [line for line in lines if '{confirm_url}' not in line]
            message = '\n'.join(lines)
            
        if not decline_url:
            lines = message.split('\n')
            lines = [line for line in lines if '{decline_url}' not in line]
            message = '\n'.join(lines)
        
        return message
    
    def _compress_image(self, image_base64, max_size_mb=1.0, quality=80):
        """Compress image if it's too large - optimized for WhatsApp Web compatibility"""
        if not PIL_AVAILABLE:
            _logger.warning('PIL not available, skipping compression')
            return image_base64
        
        try:
            # Decode base64
            image_data = base64.b64decode(image_base64)
            original_size_mb = len(image_data) / (1024 * 1024)
            original_size_kb = original_size_mb * 1024
            
            # If image is smaller than max_size, return as is
            if original_size_mb <= max_size_mb:
                _logger.info(f'Image size ({original_size_kb:.0f} KB) is acceptable, no compression needed')
                return image_base64
            
            _logger.info(f'Compressing image from {original_size_kb:.0f} KB to max {max_size_mb * 1024:.0f} KB')
            
            # Open image
            img = Image.open(io.BytesIO(image_data))
            original_width, original_height = img.size
            _logger.info(f'Original image dimensions: {original_width}x{original_height}')
            
            # Convert to RGB if necessary (for JPEG)
            if img.mode in ('RGBA', 'LA', 'P'):
                # Create white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            # First, resize if image is very large (max 1500px for better compression)
            max_dimension = 1500
            if img.width > max_dimension or img.height > max_dimension:
                _logger.info(f'Resizing image from {img.width}x{img.height} to max {max_dimension}px')
                img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
            
            # Compress image with progressive quality reduction
            output = io.BytesIO()
            current_quality = quality
            target_size_bytes = int(max_size_mb * 1024 * 1024)
            
            # Try different quality levels until we get the desired size
            while current_quality >= 30:
                output.seek(0)
                output.truncate()
                img.save(output, format='JPEG', quality=current_quality, optimize=True, progressive=True)
                compressed_size = len(output.getvalue())
                compressed_size_mb = compressed_size / (1024 * 1024)
                compressed_size_kb = compressed_size / 1024
                
                if compressed_size <= target_size_bytes:
                    _logger.info(f'Image compressed to {compressed_size_kb:.0f} KB ({compressed_size_mb:.2f} MB) with quality {current_quality}')
                    return base64.b64encode(output.getvalue()).decode('utf-8')
                
                current_quality -= 5
            
            # If still too large, resize more aggressively
            if compressed_size > target_size_bytes:
                _logger.warning('Image still too large, resizing more aggressively...')
                max_dimension = 1000
                img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
                output.seek(0)
                output.truncate()
                img.save(output, format='JPEG', quality=60, optimize=True, progressive=True)
                compressed_size = len(output.getvalue())
                compressed_size_kb = compressed_size / 1024
                _logger.info(f'Image aggressively resized and compressed to {compressed_size_kb:.0f} KB')
                return base64.b64encode(output.getvalue()).decode('utf-8')
            
            # Return the best we could do
            compressed_size_kb = len(output.getvalue()) / 1024
            _logger.warning(f'Could not compress image below {max_size_mb * 1024:.0f} KB, using {compressed_size_kb:.0f} KB')
            return base64.b64encode(output.getvalue()).decode('utf-8')
            
        except Exception as e:
            _logger.error(f'Error compressing image: {str(e)}', exc_info=True)
            # Return original if compression fails
            return image_base64
    
    def _send_message_with_image(self, phone, message, server_url):
        """Send message with image using base64 encoding"""
        if not self.invitation_image:
            _logger.warning('No invitation image found, sending text-only message')
            return self._send_text_message(phone, message, server_url)
        
        try:
            # Get image data from Binary field
            # In Odoo, Binary fields return base64-encoded string
            image_data = self.invitation_image
            filename = self.invitation_image_filename or 'invitation.jpg'
            mimetype = mimetypes.guess_type(filename)[0] or 'image/jpeg'
            
            _logger.info(f'Preparing to send image: filename={filename}, mimetype={mimetype}')
            
            # Handle different data types from Odoo Binary field
            if isinstance(image_data, bytes):
                # If it's bytes, encode to base64 string
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                _logger.info('Image data was bytes, converted to base64')
            elif isinstance(image_data, str):
                # If it's already a string, it should be base64
                image_base64 = image_data
                # Remove data URL prefix if present
                if image_base64.startswith('data:'):
                    image_base64 = image_base64.split(',', 1)[1] if ',' in image_base64 else image_base64
                    _logger.info('Removed data URL prefix from image')
                _logger.info(f'Image data is string, length: {len(image_base64)}')
            else:
                # Try to convert to string
                image_base64 = str(image_data)
                _logger.warning(f'Image data was unexpected type: {type(image_data)}, converted to string')
            
            # Validate base64 string (basic check)
            if not image_base64 or len(image_base64) < 100:
                _logger.error(f'Invalid base64 image data: too short or empty (length: {len(image_base64) if image_base64 else 0})')
                raise ValueError('Invalid image data')
            
            # Compress image if it's too large (max 1 MB for WhatsApp compatibility)
            # WhatsApp Web works better with images under 1 MB
            image_base64 = self._compress_image(image_base64, max_size_mb=1.0, quality=80)
            compressed_size_mb = (len(image_base64) * 3 / 4) / (1024 * 1024)  # Approximate size
            _logger.info(f'Final image size: {compressed_size_mb:.2f} MB ({compressed_size_mb * 1024:.0f} KB)')
            
            # Update filename to .jpg if compressed
            if PIL_AVAILABLE and not filename.lower().endswith('.jpg'):
                filename = filename.rsplit('.', 1)[0] + '.jpg'
                mimetype = 'image/jpeg'
            
            # Send request with base64 image
            send_url = f'{server_url}/api/send-media'
            payload = {
                'phoneNumber': phone,
                'message': message,
                'mediaBase64': image_base64,
                'mediaMimetype': mimetype,
                'mediaFilename': filename
            }
            
            _logger.info(f'Sending image to {send_url}, payload size: {len(json.dumps(payload))} bytes')
            
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                send_url,
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=60) as response:
                response_data = json.loads(response.read().decode())
                _logger.info(f'Server response: {response_data}')
                if not response_data.get('success'):
                    _logger.error(f'Server returned error: {response_data.get("error")}')
                return response_data
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if hasattr(e, 'read') else str(e)
            _logger.error(f'HTTP error sending image: {e.code} - {error_body}', exc_info=True)
            
            # If image sending failed, try sending text only as fallback
            if 'Evaluation failed' in error_body or '500' in str(e.code):
                _logger.warning('Image sending failed, falling back to text-only message')
                try:
                    return self._send_text_message(phone, message, server_url)
                except Exception as fallback_error:
                    _logger.error(f'Fallback to text also failed: {str(fallback_error)}')
                    raise UserError(f'Failed to send image, and text fallback also failed: {str(fallback_error)}')
            
            raise UserError(f'Error sending image: HTTP {e.code} - {error_body}')
        except Exception as e:
            _logger.error(f'Error sending message with image: {str(e)}', exc_info=True)
            
            # If image sending failed, try sending text only as fallback
            if 'Evaluation failed' in str(e) or '500' in str(e):
                _logger.warning('Image sending failed, falling back to text-only message')
                try:
                    return self._send_text_message(phone, message, server_url)
                except Exception as fallback_error:
                    _logger.error(f'Fallback to text also failed: {str(fallback_error)}')
                    raise UserError(f'Failed to send image, and text fallback also failed: {str(fallback_error)}')
            
            raise UserError(f'Error sending image: {str(e)}')
    
    def _send_text_message(self, phone, message, server_url):
        """Send text-only message"""
        send_url = f'{server_url}/api/send-message'
        payload = {
            'phoneNumber': phone,
            'message': message
        }
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            send_url,
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    
    def action_send_invitations(self):
        """Send WhatsApp invitations to selected guests"""
        self.ensure_one()
        
        if not self.guest_ids:
            raise UserError('Please select at least one guest to send invitations to.')
        
        # Get server configuration
        server_url = self._get_server_url()
        delay = self._get_delay()
        
        # Check send mode - if image exists, default to 'with_image'
        send_mode = self.send_mode
        if not send_mode and self.invitation_image:
            send_mode = 'with_image'
        elif not send_mode:
            send_mode = 'text_only'
        
        has_image = bool(self.invitation_image) and send_mode == 'with_image'
        _logger.info(f'Sending invitations: send_mode={send_mode}, has_image={has_image}, image_present={bool(self.invitation_image)}')
        
        results = []
        errors = []
        
        try:
            # Check server status first
            status_url = f'{server_url}/api/status'
            req = urllib.request.Request(status_url)
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status != 200:
                    raise UserError(f'Cannot connect to WhatsApp server. Please check if the server is running at {server_url}')
                
                status_data = json.loads(response.read().decode())
                if not status_data.get('ready'):
                    raise UserError('WhatsApp server is not ready. Please scan the QR code first.')
            
            # Send invitations one by one to track status
            for guest in self.guest_ids:
                phone = guest._format_phone_number()
                if not phone:
                    guest.write({
                        'invitation_status': 'failed',
                        'invitation_error': 'Invalid phone number format'
                    })
                    errors.append({
                        'guest': guest.name,
                        'error': 'Invalid phone number format'
                    })
                    continue
                
                try:
                    # Personalize message for this guest
                    personalized_message = self._personalize_message(guest)
                    
                    # Send message (with or without image)
                    if has_image:
                        response_data = self._send_message_with_image(phone, personalized_message, server_url)
                    else:
                        response_data = self._send_text_message(phone, personalized_message, server_url)
                    
                    if response_data.get('success'):
                        guest.write({
                            'invitation_status': 'sent',
                            'invitation_sent_date': fields.Datetime.now(),
                            'message_id': response_data.get('messageId', ''),
                            'invitation_error': False
                        })
                        results.append({
                            'guest': guest.name,
                            'success': True
                        })
                    else:
                        error_msg = response_data.get('error', 'Unknown error')
                        guest.write({
                            'invitation_status': 'failed',
                            'invitation_error': error_msg,
                            'invitation_sent_date': fields.Datetime.now()
                        })
                        errors.append({
                            'guest': guest.name,
                            'error': error_msg
                        })
                    
                    # Delay between messages
                    time.sleep(delay / 1000.0)
                    
                except urllib.error.URLError as e:
                    error_msg = f'Connection error: {str(e)}'
                    guest.write({
                        'invitation_status': 'failed',
                        'invitation_error': error_msg,
                        'invitation_sent_date': fields.Datetime.now()
                    })
                    errors.append({
                        'guest': guest.name,
                        'error': error_msg
                    })
                except Exception as e:
                    error_msg = f'Error: {str(e)}'
                    guest.write({
                        'invitation_status': 'failed',
                        'invitation_error': error_msg,
                        'invitation_sent_date': fields.Datetime.now()
                    })
                    errors.append({
                        'guest': guest.name,
                        'error': error_msg
                    })
            
            # Prepare result message
            total = len(self.guest_ids)
            sent = len(results)
            failed = len(errors)
            
            message = f'Invitations sent: {sent}/{total}'
            if has_image:
                message += ' (with image)'
            message += '\n'
            
            if failed > 0:
                message += f'Failed: {failed}\n'
                message += '\nErrors:\n'
                for error in errors[:5]:  # Show first 5 errors
                    message += f"- {error['guest']}: {error['error']}\n"
                if failed > 5:
                    message += f'... and {failed - 5} more errors.\n'
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'WhatsApp Invitations',
                    'message': message,
                    'type': 'success' if failed == 0 else 'warning',
                    'sticky': False,
                }
            }
            
        except urllib.error.URLError:
            raise UserError(f'Cannot connect to WhatsApp server at {server_url}. Please make sure the server is running.')
        except Exception as e:
            _logger.error(f'Error sending WhatsApp invitations: {str(e)}', exc_info=True)
            raise UserError(f'Error sending invitations: {str(e)}')
