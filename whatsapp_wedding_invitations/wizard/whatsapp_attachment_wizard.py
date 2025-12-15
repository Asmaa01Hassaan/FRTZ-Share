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

_logger = logging.getLogger(__name__)


class WhatsAppAttachmentWizard(models.TransientModel):
    _name = 'whatsapp.attachment.wizard'
    _description = 'WhatsApp Attachment Wizard'

    event_id = fields.Many2one(
        'calendar.event',
        string='Event',
        required=True,
        readonly=True
    )
    
    guest_ids = fields.Many2many(
        'event.guest',
        'whatsapp_attachment_guest_rel',
        'wizard_id',
        'guest_id',
        string='Guests',
        required=True,
        help='Select guests to send attachments to'
    )
    
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'whatsapp_attachment_wizard_attachment_rel',
        'wizard_id',
        'attachment_id',
        string='Attachments',
        required=True,
        help='Select attachments to send'
    )
    
    message = fields.Text(
        string='Message',
        default='Please find the attached files.',
        help='Message to send with attachments'
    )
    
    send_progress = fields.Text(
        string='Progress',
        readonly=True,
        help='Progress of sending attachments'
    )
    
    @api.model
    def default_get(self, fields_list):
        """Set default values from context"""
        res = super(WhatsAppAttachmentWizard, self).default_get(fields_list)
        
        if 'event_id' in fields_list and 'default_event_id' in self._context:
            res['event_id'] = self._context['default_event_id']
        
        if 'guest_ids' in fields_list:
            default_guests = self._context.get('default_guest_ids')
            if default_guests:
                res['guest_ids'] = [(6, 0, list(default_guests))]
        
        if 'attachment_ids' in fields_list:
            default_attachments = self._context.get('default_attachment_ids')
            if default_attachments:
                res['attachment_ids'] = [(6, 0, list(default_attachments))]
        
        return res
    
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
    
    def _send_attachment(self, phone, attachment, message, server_url):
        """Send attachment via WhatsApp"""
        try:
            # Get attachment data
            if not attachment.datas:
                raise ValueError(f'Attachment {attachment.name} has no data')
            
            # Handle different data types from Odoo attachment
            # In Odoo, attachment.datas is always stored as base64 string
            # But it might be returned as bytes (UTF-8 encoded base64 string)
            if isinstance(attachment.datas, bytes):
                # attachment.datas is bytes - likely UTF-8 encoded base64 string, NOT raw binary
                # Try to decode as UTF-8 string first
                try:
                    media_base64 = attachment.datas.decode('utf-8')
                    file_data = base64.b64decode(media_base64)
                    _logger.info(f'Attachment data was bytes (UTF-8 base64 string), decoded successfully (length: {len(file_data)} bytes)')
                except (UnicodeDecodeError, ValueError) as e:
                    # If UTF-8 decode fails, it might be raw binary data (rare case)
                    _logger.warning(f'Could not decode as UTF-8, treating as raw binary: {str(e)}')
                    media_base64 = base64.b64encode(attachment.datas).decode('utf-8')
                    file_data = attachment.datas
            elif isinstance(attachment.datas, str):
                # If it's already a string, it should be base64
                media_base64 = attachment.datas
                # Remove data URL prefix if present
                if media_base64.startswith('data:'):
                    media_base64 = media_base64.split(',', 1)[1] if ',' in media_base64 else media_base64
                    _logger.info('Removed data URL prefix from attachment data')
                
                # Clean base64 string (remove whitespace, newlines, etc.)
                media_base64 = media_base64.strip().replace('\n', '').replace('\r', '').replace(' ', '')
                
                # Validate base64 string format
                try:
                    # Try to decode to verify it's valid base64
                    file_data = base64.b64decode(media_base64, validate=True)
                    
                    # Verify decoded data is not empty
                    if len(file_data) == 0:
                        raise ValueError('Decoded base64 data is empty')
                    
                    # For images, verify file header
                    if mimetype and mimetype.startswith('image/'):
                        header = file_data[:4]
                        if mimetype == 'image/jpeg':
                            if not (header[0] == 0xFF and header[1] == 0xD8):
                                _logger.warning(f'JPEG header mismatch: got {header.hex()}, expected FFD8')
                        elif mimetype == 'image/png':
                            if header[:4] != b'\x89PNG':
                                _logger.warning(f'PNG header mismatch: got {header.hex()}, expected 89504E47')
                    
                    _logger.info(f'Attachment data is valid base64 string (decoded length: {len(file_data)} bytes)')
                except Exception as decode_error:
                    _logger.error(f'Invalid base64 data: {str(decode_error)}')
                    raise ValueError(f'Invalid base64 data in attachment: {str(decode_error)}')
            else:
                # Try to convert to string (shouldn't happen, but just in case)
                _logger.warning(f'Unexpected attachment data type: {type(attachment.datas)}, converting to string')
                media_base64 = str(attachment.datas)
                try:
                    file_data = base64.b64decode(media_base64, validate=True)
                except Exception:
                    raise ValueError(f'Cannot decode attachment data as base64')
            
            file_size = len(file_data)
            file_size_mb = file_size / (1024 * 1024)
            
            # Check file size (WhatsApp limit is usually 16MB, but we'll use 10MB to be safe)
            if file_size_mb > 10:
                raise ValueError(f'Attachment {attachment.name} is too large ({file_size_mb:.2f} MB). Maximum size is 10 MB.')
            
            # Get mimetype
            mimetype = attachment.mimetype or mimetypes.guess_type(attachment.name)[0] or 'application/octet-stream'
            
            _logger.info(f'Sending attachment: {attachment.name}, size: {file_size_mb:.2f} MB, mimetype: {mimetype}')
            
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
            
            # Send request
            send_url = f'{server_url}/api/send-media'
            payload = {
                'phoneNumber': phone,
                'message': message or f'Please find attached: {attachment.name}',
                'mediaBase64': media_base64,  # Base64 string
                'mediaMimetype': mimetype,
                'mediaFilename': attachment.name
            }
            
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                send_url,
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=60) as response:
                response_data = json.loads(response.read().decode())
                return response_data
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if hasattr(e, 'read') else str(e)
            _logger.error(f'HTTP error sending attachment: {e.code} - {error_body}', exc_info=True)
            raise UserError(f'Error sending attachment: HTTP {e.code} - {error_body}')
        except Exception as e:
            _logger.error(f'Error sending attachment: {str(e)}', exc_info=True)
            raise UserError(f'Error sending attachment: {str(e)}')
    
    def action_send_attachments(self):
        """Send WhatsApp attachments to selected guests"""
        self.ensure_one()
        
        if not self.guest_ids:
            raise UserError('Please select at least one guest to send attachments to.')
        
        if not self.attachment_ids:
            raise UserError('Please select at least one attachment to send.')
        
        # Get server configuration
        server_url = self._get_server_url()
        delay = self._get_delay()
        
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
            
            # Send attachments to each guest
            total_operations = len(self.guest_ids) * len(self.attachment_ids)
            current_operation = 0
            
            for guest in self.guest_ids:
                phone = guest._format_phone_number()
                if not phone:
                    errors.append({
                        'guest': guest.name,
                        'attachment': 'All',
                        'error': 'Invalid phone number format'
                    })
                    continue
                
                # Send each attachment to this guest
                for attachment in self.attachment_ids:
                    current_operation += 1
                    try:
                        # Personalize message for this guest
                        personalized_message = self.message.replace('{name}', guest.name or 'Guest')
                        
                        # Send attachment
                        response_data = self._send_attachment(phone, attachment, personalized_message, server_url)
                        
                        if response_data.get('success'):
                            results.append({
                                'guest': guest.name,
                                'attachment': attachment.name,
                                'success': True
                            })
                        else:
                            error_msg = response_data.get('error', 'Unknown error')
                            errors.append({
                                'guest': guest.name,
                                'attachment': attachment.name,
                                'error': error_msg
                            })
                        
                        # Delay between attachments
                        if current_operation < total_operations:
                            time.sleep(delay / 1000.0)
                        
                    except Exception as e:
                        error_msg = f'Error: {str(e)}'
                        errors.append({
                            'guest': guest.name,
                            'attachment': attachment.name,
                            'error': error_msg
                        })
                
                # Delay between guests
                if guest != self.guest_ids[-1]:
                    time.sleep(delay / 1000.0)
            
            # Prepare result message
            total = len(self.guest_ids) * len(self.attachment_ids)
            sent = len(results)
            failed = len(errors)
            
            message = f'Attachments sent: {sent}/{total}\n'
            
            if failed > 0:
                message += f'Failed: {failed}\n'
                message += '\nErrors:\n'
                for error in errors[:5]:  # Show first 5 errors
                    message += f"- {error['guest']} - {error['attachment']}: {error['error']}\n"
                if failed > 5:
                    message += f'... and {failed - 5} more errors.\n'
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'WhatsApp Attachments',
                    'message': message,
                    'type': 'success' if failed == 0 else 'warning',
                    'sticky': False,
                }
            }
            
        except urllib.error.URLError:
            raise UserError(f'Cannot connect to WhatsApp server at {server_url}. Please make sure the server is running.')
        except Exception as e:
            _logger.error(f'Error sending WhatsApp attachments: {str(e)}', exc_info=True)
            raise UserError(f'Error sending attachments: {str(e)}')

