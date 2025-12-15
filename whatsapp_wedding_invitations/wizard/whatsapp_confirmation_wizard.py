# -*- coding: utf-8 -*-

import json
import logging
import urllib.request
import urllib.error
import time
import random
import base64
import mimetypes

from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class WhatsAppConfirmationWizard(models.TransientModel):
    _name = 'whatsapp.confirmation.wizard'
    _description = 'WhatsApp RSVP Confirmation Wizard'
    
    event_id = fields.Many2one(
        'calendar.event',
        string='Event',
        required=True
    )
    
    guest_ids = fields.Many2many(
        'event.guest',
        string='Guests',
        domain="[('calendar_event_id', '=', event_id)]"
    )
    
    message_template = fields.Text(
        string='Message Template',
        default=lambda self: self._default_message_template(),
        help="""Available placeholders:
        {name} - Guest name
        {event_name} - Event name
        {event_date} - Event date
        {confirm_url} - Confirmation link
        {decline_url} - Decline link"""
    )
    
    confirmation_method = fields.Selection([
        ('message', 'Message Only 💬'),
        ('links', 'Message + Links 🔗'),
        ('attachments', 'Attachments with Message Caption 📎💬'),
        ('attachments_message', 'Attachments + Separate Message 📎💬💬'),
        ('attachments_links', 'Attachments + Links 📎🔗'),
    ], string='Confirmation Method', default='attachments',
       help='''Choose what to send:
• Message Only: Just the text message
• Message + Links: Text message with confirmation links
• Attachments with Message Caption: Image/files with message as caption (recommended)
• Attachments + Separate Message: Image/files then separate text message
• Attachments + Links: Image/files with message caption including links''')
    
    # Attachment fields
    include_attachments = fields.Boolean(
        string='Include Attachments',
        compute='_compute_include_attachments',
        store=False
    )
    
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'whatsapp_confirm_wizard_attachment_rel',
        'wizard_id',
        'attachment_id',
        string='Attachments 📎',
        help='Attachments to send with the invitation (images, PDFs, etc.)'
    )
    
    include_links = fields.Boolean(
        string='Include Confirmation Links',
        default=True,
        help='Include clickable links for confirm/decline'
    )
    
    include_text_response = fields.Boolean(
        string='Allow Text Response',
        default=True,
        help='Include instructions for text-based response'
    )
    
    send_progress = fields.Char(string='Progress', readonly=True)
    
    @api.model
    def _default_message_template(self):
        return """المكرمة *{name}* 💒
السلام عليكم ورحمة الله،

بكل حب وود تتشرف 
*السيدة جميلة بنت عثمان آل عبد العزيز والسيدة فايزة بنت أحمد آل طالع* 
ندعوك  لتاكيد الحضور ✨ *{event_name}* ✨

━━━━━━━━━━━━━━

💬 نرجو الرد للتاكيد حضوركم :
• أرسل *نعم* للتأكيد ✅
• أرسل *لا* للاعتذار ❌

━━━━━━━━━━━━━━

نتطلع لرؤيتك! 💕"""
    
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        
        # Get event from context
        event_id = self.env.context.get('default_event_id') or self.env.context.get('active_id')
        if event_id:
            res['event_id'] = event_id
            
            # Get guests that haven't been sent confirmation yet
            event = self.env['calendar.event'].browse(event_id)
            pending_guests = event.event_guest_ids.filtered(
                lambda g: g.rsvp_status == 'pending' and not g.confirmation_sent
            )
            res['guest_ids'] = [(6, 0, pending_guests.ids)]
        
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
    
    @api.depends('confirmation_method')
    def _compute_include_attachments(self):
        """Compute if attachments should be included based on confirmation method"""
        for wizard in self:
            wizard.include_attachments = wizard.confirmation_method in ('attachments', 'attachments_message', 'attachments_links')
    
    def _send_attachment(self, phone, attachment, message, server_url):
        """Send attachment via WhatsApp"""
        try:
            # Get attachment data
            if not attachment.datas:
                raise ValueError(f'Attachment {attachment.name} has no data')
            
            # Handle different data types from Odoo attachment
            if isinstance(attachment.datas, bytes):
                try:
                    media_base64 = attachment.datas.decode('utf-8')
                    file_data = base64.b64decode(media_base64)
                except (UnicodeDecodeError, ValueError):
                    media_base64 = base64.b64encode(attachment.datas).decode('utf-8')
                    file_data = attachment.datas
            elif isinstance(attachment.datas, str):
                media_base64 = attachment.datas
                if media_base64.startswith('data:'):
                    media_base64 = media_base64.split(',', 1)[1] if ',' in media_base64 else media_base64
                media_base64 = media_base64.strip().replace('\n', '').replace('\r', '').replace(' ', '')
                file_data = base64.b64decode(media_base64, validate=True)
            else:
                media_base64 = str(attachment.datas)
                file_data = base64.b64decode(media_base64, validate=True)
            
            file_size = len(file_data)
            file_size_mb = file_size / (1024 * 1024)
            
            if file_size_mb > 10:
                raise ValueError(f'Attachment {attachment.name} is too large ({file_size_mb:.2f} MB). Maximum 10 MB.')
            
            # Get mimetype
            mimetype = attachment.mimetype or mimetypes.guess_type(attachment.name)[0] or 'application/octet-stream'
            
            _logger.info(f'Sending attachment: {attachment.name}, size: {file_size_mb:.2f} MB, mimetype: {mimetype}')
            
            # Send request
            send_url = f'{server_url}/api/send-media'
            payload = {
                'phoneNumber': phone,
                'message': message or f'📎 {attachment.name}',
                'mediaBase64': media_base64,
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
            _logger.error(f'HTTP error sending attachment: {e.code} - {error_body}')
            return {'success': False, 'error': f'HTTP {e.code}: {error_body}'}
        except Exception as e:
            _logger.error(f'Error sending attachment: {str(e)}')
            return {'success': False, 'error': str(e)}
    
    def _personalize_message(self, guest):
        """Personalize message template for a specific guest"""
        message = self.message_template or self._default_message_template()
        
        # Format event date
        event_date = ''
        if guest.event_id.start:
            event_date = fields.Datetime.context_timestamp(
                self, guest.event_id.start
            ).strftime('%d/%m/%Y %H:%M')
        
        # Get confirmation URLs
        confirm_url = guest.get_confirmation_url() if self.include_links else ''
        decline_url = guest.get_decline_url() if self.include_links else ''
        
        # Replace placeholders
        message = message.replace('{name}', guest.name or '')
        message = message.replace('{event_name}', guest.event_id.name or '')
        message = message.replace('{event_date}', event_date)
        message = message.replace('{confirm_url}', confirm_url)
        message = message.replace('{decline_url}', decline_url)
        
        # Remove link lines if not including links
        if not self.include_links:
            lines = message.split('\n')
            lines = [l for l in lines if '{confirm_url}' not in l and '{decline_url}' not in l]
            message = '\n'.join(lines)
        
        # Remove text response instructions if not including
        if not self.include_text_response:
            lines = message.split('\n')
            lines = [l for l in lines if 'أرسل:' not in l and 'Send:' not in l]
            message = '\n'.join(lines)
        
        return message
    
    def _send_message(self, phone, message, server_url):
        """Send WhatsApp message"""
        try:
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
                response_data = json.loads(response.read().decode())
                return response_data
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if hasattr(e, 'read') else str(e)
            _logger.error(f'HTTP error sending confirmation: {e.code} - {error_body}')
            raise UserError(f'Error sending confirmation: HTTP {e.code}')
        except Exception as e:
            _logger.error(f'Error sending confirmation: {str(e)}')
            raise UserError(f'Error sending confirmation: {str(e)}')
    
    def _send_poll(self, phone, question, options, server_url):
        """Send WhatsApp poll for RSVP"""
        try:
            send_url = f'{server_url}/api/send-poll'
            payload = {
                'phoneNumber': phone,
                'question': question,
                'options': options,
                'allowMultipleAnswers': False
            }
            
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                send_url,
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                response_data = json.loads(response.read().decode())
                return response_data
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if hasattr(e, 'read') else str(e)
            _logger.error(f'HTTP error sending poll: {e.code} - {error_body}')
            return {'success': False, 'error': f'HTTP {e.code}: {error_body}'}
        except Exception as e:
            _logger.error(f'Error sending poll: {str(e)}')
            return {'success': False, 'error': str(e)}
    
    def action_send_confirmations(self):
        """Send RSVP confirmation requests to selected guests"""
        self.ensure_one()
        
        if not self.guest_ids:
            raise UserError('Please select at least one guest')
        
        server_url = self._get_server_url()
        delay_ms = self._get_delay()
        
        # Check server status
        try:
            status_url = f'{server_url}/api/status'
            with urllib.request.urlopen(status_url, timeout=10) as response:
                status = json.loads(response.read().decode())
                # API returns 'ready' not 'isReady'
                if not status.get('ready') and not status.get('isReady'):
                    raise UserError('WhatsApp is not connected. Please scan QR code first.')
        except urllib.error.URLError:
            raise UserError(f'Cannot connect to WhatsApp server at {server_url}')
        
        sent_count = 0
        failed_count = 0
        errors = []
        
        for i, guest in enumerate(self.guest_ids):
            # Update progress
            self.write({'send_progress': f'Sending {i+1}/{len(self.guest_ids)}...'})
            self.env.cr.commit()
            
            # Get phone number
            phone = guest._format_phone_number()
            if not phone:
                errors.append(f'{guest.name}: Invalid phone number')
                failed_count += 1
                continue
            
            # Generate confirmation token if not exists
            if not guest.confirmation_token:
                guest.regenerate_token()
            
            # Personalize message
            message = self._personalize_message(guest)
            
            try:
                message_sent = False
                attachments_sent = False
                
                # Send attachments first (if method includes attachments)
                if self.confirmation_method in ('attachments', 'attachments_message', 'attachments_links') and self.attachment_ids:
                    for idx, attachment in enumerate(self.attachment_ids):
                        # Use personalized message as caption for first attachment
                        # For subsequent attachments, use empty caption to avoid duplicate messages
                        if idx == 0:
                            att_message = message  # Use the full personalized message template
                        else:
                            att_message = ''  # No caption for additional attachments
                        
                        att_result = self._send_attachment(phone, attachment, att_message, server_url)
                        if att_result.get('success'):
                            attachments_sent = True
                            _logger.info(f'Attachment {attachment.name} sent to {guest.name}')
                        else:
                            _logger.warning(f'Failed to send attachment {attachment.name} to {guest.name}: {att_result.get("error")}')
                        
                        # Small delay between attachments
                        time.sleep(1)
                
                # Send text message (if method requires separate message)
                # - 'message' and 'links': always send text message
                # - 'attachments': message is sent as caption, no separate message needed
                # - 'attachments_message': send attachments then separate message
                # - 'attachments_links': message with links is sent as caption, no separate message
                send_separate_message = (
                    self.confirmation_method in ('message', 'links') or 
                    (self.confirmation_method == 'attachments_message')
                )
                
                if send_separate_message:
                    # Small delay after attachments
                    if attachments_sent:
                        time.sleep(1)
                    
                    result = self._send_message(phone, message, server_url)
                    if result.get('success'):
                        message_sent = True
                        _logger.info(f'Confirmation message sent to {guest.name}')
                    else:
                        _logger.warning(f'Failed to send message to {guest.name}: {result.get("error")}')
                
                # Update guest record if at least one method succeeded
                if message_sent or attachments_sent:
                    guest.write({
                        'confirmation_sent': True,
                        'confirmation_sent_date': fields.Datetime.now(),
                        'message_id': result.get('messageId', '') if message_sent else '',
                    })
                    sent_count += 1
                else:
                    errors.append(f'{guest.name}: Failed to send confirmation')
                    failed_count += 1
                    
            except Exception as e:
                errors.append(f'{guest.name}: {str(e)}')
                failed_count += 1
                _logger.error(f'Error sending to {guest.name}: {str(e)}')
            
            # Delay between messages
            if i < len(self.guest_ids) - 1:
                time.sleep(delay_ms / 1000)
        
        # Prepare result message
        result_message = f'Confirmation requests sent: {sent_count}/{len(self.guest_ids)}'
        if failed_count > 0:
            result_message += f'\nFailed: {failed_count}'
            result_message += f'\nErrors:\n' + '\n'.join(f'- {e}' for e in errors[:5])
            if len(errors) > 5:
                result_message += f'\n... and {len(errors) - 5} more errors'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'RSVP Confirmations Sent',
                'message': result_message,
                'type': 'success' if failed_count == 0 else 'warning',
                'sticky': True,
            }
        }

