# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import urllib.request
import urllib.error
import json
import logging
import time

_logger = logging.getLogger(__name__)


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
    
    send_progress = fields.Text(
        string='Progress',
        readonly=True,
        help='Progress of sending invitations'
    )
    
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
        """Get delay between messages from settings"""
        return int(self.env['ir.config_parameter'].sudo().get_param(
            'whatsapp_wedding_invitations.delay_between_messages',
            '2000'
        ))
    
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
        
        # Replace placeholders
        replacements = {
            '{name}': guest.name or '',
            '{guestName}': guest.name.split()[0] if guest.name else guest.name or '',
            '{event_name}': event.name or 'Event',
            '{date}': event._format_event_date(),
            '{venue}': event._get_venue(),
            '{time}': event._format_event_time(),
            '{organizer}': event.user_id.name if event.user_id else 'Organizer',
        }
        
        for placeholder, value in replacements.items():
            message = message.replace(placeholder, value)
        
        return message
    
    def action_send_invitations(self):
        """Send WhatsApp invitations to selected guests"""
        self.ensure_one()
        
        if not self.guest_ids:
            raise UserError('Please select at least one guest to send invitations to.')
        
        # Get server configuration
        server_url = self._get_server_url()
        delay = self._get_delay()
        
        # Prepare guests data
        guests_data = []
        for guest in self.guest_ids:
            phone = guest._format_phone_number()
            if not phone:
                continue
            guests_data.append(self._prepare_guest_data(guest))
        
        if not guests_data:
            raise UserError('No valid phone numbers found in selected guests.')
        
        # Prepare personalized messages for each guest
        # We'll use the first guest's personalized message as template
        # and let the server handle personalization
        first_guest = self.guest_ids[0]
        template_message = self._personalize_message(first_guest)
        
        # For bulk sending, we need to send individual requests or modify server
        # For now, let's send individually to track each guest's status
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
                    
                    # Send message
                    send_url = f'{server_url}/api/send-message'
                    payload = {
                        'phoneNumber': phone,
                        'message': personalized_message
                    }
                    
                    data = json.dumps(payload).encode('utf-8')
                    req = urllib.request.Request(
                        send_url,
                        data=data,
                        headers={'Content-Type': 'application/json'}
                    )
                    
                    with urllib.request.urlopen(req, timeout=30) as response:
                        if response.status == 200:
                            response_data = json.loads(response.read().decode())
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
                        else:
                            error_msg = f'HTTP {response.status}: {response.read().decode()}'
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
            
            message = f'Invitations sent: {sent}/{total}\n'
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


class EventWhatsAppInvitationWizard(models.TransientModel):
    _name = 'event.whatsapp.invitation.wizard'
    _description = 'Event WhatsApp Invitation Wizard'

    event_id = fields.Many2one(
        'event.event',
        string='Event',
        required=True,
        readonly=True,
    )
    registration_ids = fields.Many2many(
        'event.registration',
        'event_whatsapp_invitation_registration_rel',
        'wizard_id',
        'registration_id',
        string='Registrations',
        required=True,
        help='Select registrations to notify via WhatsApp.',
    )
    message_template = fields.Text(
        string='Message Template',
        required=True,
        help='Use {name}, {event_name}, {date}, {venue}, {time}, {organizer} placeholders.',
    )
    send_progress = fields.Text(
        string='Progress',
        readonly=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super(EventWhatsAppInvitationWizard, self).default_get(fields_list)

        if 'event_id' in fields_list and 'default_event_id' in self._context:
            res['event_id'] = self._context['default_event_id']

        if 'registration_ids' in fields_list:
            default_regs = self._context.get('default_registration_ids')
            if default_regs:
                res['registration_ids'] = self._format_registration_defaults(default_regs)

        if 'message_template' in fields_list and 'default_message_template' in self._context:
            res['message_template'] = self._context['default_message_template']
        elif 'message_template' in fields_list and res.get('event_id'):
            event = self.env['event.event'].browse(res['event_id'])
            res['message_template'] = event.whatsapp_message_template or event._default_whatsapp_invitation_template()

        return res

    def _format_registration_defaults(self, value):
        if isinstance(value, (list, tuple)):
            if value and isinstance(value[0], (list, tuple)):
                first = value[0]
                if len(first) >= 3 and isinstance(first[0], int):
                    return [tuple(cmd) for cmd in value]
            return [(6, 0, list(value))]
        return [(6, 0, [value])]

    def _get_server_url(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'whatsapp_wedding_invitations.server_url',
            'http://localhost:3000'
        )

    def _get_delay(self):
        return int(self.env['ir.config_parameter'].sudo().get_param(
            'whatsapp_wedding_invitations.delay_between_messages',
            '2000'
        ))

    def _personalize_message(self, registration):
        event = self.event_id
        message = self.message_template
        guest_name = registration.name or (registration.partner_id.name if registration.partner_id else '')
        first_name = guest_name.split()[0] if guest_name else guest_name
        replacements = {
            '{name}': guest_name or '',
            '{guestName}': first_name or '',
            '{event_name}': event.name or 'Event',
            '{date}': event._format_event_date(),
            '{venue}': event._get_venue(),
            '{time}': event._format_event_time(),
            '{organizer}': event.organizer_id.name if event.organizer_id else (event.user_id.name if event.user_id else 'Organizer'),
        }
        for placeholder, value in replacements.items():
            message = message.replace(placeholder, value)
        return message

    def action_send_invitations(self):
        self.ensure_one()
        if not self.registration_ids:
            raise UserError('Please select at least one registration.')

        server_url = self._get_server_url()
        delay = self._get_delay()
        results = []
        errors = []

        try:
            status_url = f'{server_url}/api/status'
            req = urllib.request.Request(status_url)
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status != 200:
                    raise UserError(f'Cannot connect to WhatsApp server. Please check if the server is running at {server_url}')
                status_data = json.loads(response.read().decode())
                if not status_data.get('ready'):
                    raise UserError('WhatsApp server is not ready. Please scan the QR code first.')

            for registration in self.registration_ids:
                phone = registration._format_phone_number_for_whatsapp()
                if not phone:
                    registration.write({
                        'whatsapp_invitation_status': 'failed',
                        'whatsapp_invitation_error': 'Invalid phone number format',
                    })
                    errors.append({
                        'guest': registration.name,
                        'error': 'Invalid phone number format',
                    })
                    continue

                try:
                    personalized_message = self._personalize_message(registration)
                    send_url = f'{server_url}/api/send-message'
                    payload = {
                        'phoneNumber': phone,
                        'message': personalized_message,
                    }
                    data = json.dumps(payload).encode('utf-8')
                    req = urllib.request.Request(
                        send_url,
                        data=data,
                        headers={'Content-Type': 'application/json'}
                    )
                    with urllib.request.urlopen(req, timeout=30) as response:
                        if response.status == 200:
                            response_data = json.loads(response.read().decode())
                            if response_data.get('success'):
                                registration.write({
                                    'whatsapp_invitation_status': 'sent',
                                    'whatsapp_invitation_sent_date': fields.Datetime.now(),
                                    'whatsapp_message_id': response_data.get('messageId', ''),
                                    'whatsapp_invitation_error': False,
                                })
                                results.append({
                                    'guest': registration.name,
                                    'success': True,
                                })
                            else:
                                error_msg = response_data.get('error', 'Unknown error')
                                registration.write({
                                    'whatsapp_invitation_status': 'failed',
                                    'whatsapp_invitation_error': error_msg,
                                    'whatsapp_invitation_sent_date': fields.Datetime.now(),
                                })
                                errors.append({
                                    'guest': registration.name,
                                    'error': error_msg,
                                })
                        else:
                            error_msg = f'HTTP {response.status}: {response.read().decode()}'
                            registration.write({
                                'whatsapp_invitation_status': 'failed',
                                'whatsapp_invitation_error': error_msg,
                                'whatsapp_invitation_sent_date': fields.Datetime.now(),
                            })
                            errors.append({
                                'guest': registration.name,
                                'error': error_msg,
                            })

                    time.sleep(delay / 1000.0)

                except urllib.error.URLError as e:
                    error_msg = f'Connection error: {str(e)}'
                    registration.write({
                        'whatsapp_invitation_status': 'failed',
                        'whatsapp_invitation_error': error_msg,
                        'whatsapp_invitation_sent_date': fields.Datetime.now(),
                    })
                    errors.append({
                        'guest': registration.name,
                        'error': error_msg,
                    })
                except Exception as e:
                    error_msg = f'Error: {str(e)}'
                    registration.write({
                        'whatsapp_invitation_status': 'failed',
                        'whatsapp_invitation_error': error_msg,
                        'whatsapp_invitation_sent_date': fields.Datetime.now(),
                    })
                    errors.append({
                        'guest': registration.name,
                        'error': error_msg,
                    })

            total = len(self.registration_ids)
            sent = len(results)
            failed = len(errors)
            message = f'Invitations sent: {sent}/{total}\n'
            if failed > 0:
                message += f'Failed: {failed}\n\nErrors:\n'
                for error in errors[:5]:
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