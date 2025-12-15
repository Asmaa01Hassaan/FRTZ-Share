# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    event_guest_ids = fields.One2many(
        'event.guest',
        'calendar_event_id',
        string='Guests',
        help='List of guests invited to this event'
    )
    
    guest_count = fields.Integer(
        string='Guest Count',
        compute='_compute_guest_count',
        store=True
    )
    
    invitation_sent_count = fields.Integer(
        string='Invitations Sent',
        compute='_compute_invitation_stats',
        store=True
    )
    
    invitation_failed_count = fields.Integer(
        string='Invitations Failed',
        compute='_compute_invitation_stats',
        store=True
    )
    
    # RSVP Stats
    rsvp_pending_count = fields.Integer(
        string='Pending RSVPs',
        compute='_compute_rsvp_stats',
        store=True
    )
    
    rsvp_accepted_count = fields.Integer(
        string='Accepted RSVPs',
        compute='_compute_rsvp_stats',
        store=True
    )
    
    rsvp_declined_count = fields.Integer(
        string='Declined RSVPs',
        compute='_compute_rsvp_stats',
        store=True
    )
    
    total_expected_attendees = fields.Integer(
        string='Total Expected Attendees',
        compute='_compute_rsvp_stats',
        store=True,
        help='Total number of people expected (guests + companions)'
    )
    
    def action_view_guests(self):
        """Open guest list filtered by this calendar event"""
        self.ensure_one()
        return {
            'name': f'Guests - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'event.guest',
            'view_mode': 'tree,form',
            'domain': [('calendar_event_id', '=', self.id)],
            'context': {
                'default_calendar_event_id': self.id,
                'search_default_group_by_rsvp_status': 1,
            }
        }
    
    invitation_message_template = fields.Text(
        string='Invitation Message Template',
        default=lambda self: self._default_invitation_template(),
        help='''Message template for WhatsApp invitations.
        
Available placeholders:
• {name} - Guest full name
• {guestName} - Guest first name
• {event_name} - Event name
• {date} - Event date
• {venue} - Venue/Location
• {time} - Event time
• {organizer} - Organizer name
• {image_url} - Invitation image URL
• {confirm_url} - RSVP confirm link
• {decline_url} - RSVP decline link'''
    )
    
    invitation_image = fields.Binary(
        string='Invitation Image',
        attachment=True,
        store=True,
        help='Image to send with the invitation message (optional). Supported formats: JPG, PNG, GIF.'
    )
    
    invitation_image_filename = fields.Char(
        string='Image Filename',
        help='Filename of the invitation image'
    )
    
    invitation_image_url = fields.Char(
        string='Invitation Image URL',
        help='Public URL of the invitation image. Use this if you want to include an image link in the message. The image must be publicly accessible.'
    )


    def open_related_event(self):
        self.ensure_one()

        event = self.env['event.event'].search([('calendar_event_id', '=', self.id)], limit=1)

        if not event:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'No Related Event',
                    'message': 'This calendar entry is not linked to any Event.',
                    'type': 'warning',
                    'sticky': False,
                }
            }

        return {
            'type': 'ir.actions.act_window',
            'name': 'Event',
            'res_model': 'event.event',
            'view_mode': 'list,form',
            'domain': [('calendar_event_id', '=', self.id)],
            'res_id': event.id,
            'target': 'current',
        }
    @api.depends('event_guest_ids')
    def _compute_guest_count(self):
        for record in self:
            record.guest_count = len(record.event_guest_ids)
    
    @api.depends('event_guest_ids.invitation_status')
    def _compute_invitation_stats(self):
        for record in self:
            record.invitation_sent_count = len(record.event_guest_ids.filtered(
                lambda g: g.invitation_status == 'sent'
            ))
            record.invitation_failed_count = len(record.event_guest_ids.filtered(
                lambda g: g.invitation_status == 'failed'
            ))
    
    @api.depends('event_guest_ids.rsvp_status', 'event_guest_ids.total_attendees')
    def _compute_rsvp_stats(self):
        for record in self:
            guests = record.event_guest_ids
            record.rsvp_pending_count = len(guests.filtered(lambda g: g.rsvp_status == 'pending'))
            record.rsvp_accepted_count = len(guests.filtered(lambda g: g.rsvp_status == 'accepted'))
            record.rsvp_declined_count = len(guests.filtered(lambda g: g.rsvp_status == 'declined'))
            record.total_expected_attendees = sum(guests.filtered(lambda g: g.rsvp_status == 'accepted').mapped('total_attendees'))
    
    def _default_invitation_template(self):
        return """💒 *دعوة زفاف* 💒

مرحباً *{name}*

يسعدنا دعوتك لمشاركتنا أجمل لحظات حياتنا!

✨ *{event_name}* ✨

📅 التاريخ: {date}
📍 المكان: {venue}
⏰ الوقت: {time}

┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

📸 *شاهد بطاقة الدعوة* 👇
{image_url}

┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

✅ *للتأكيد اضغط هنا* 👇
{confirm_url}

❌ *للاعتذار اضغط هنا* 👇
{decline_url}

┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

نتشرف بحضوركم! 💕

مع حبنا،
{organizer}"""
    
    def action_send_whatsapp_invitations(self):
        """Open wizard to send WhatsApp invitations"""
        self.ensure_one()
        
        if not self.event_guest_ids:
            raise UserError('Please add guests to the event before sending invitations.')
        
        # Filter guests with phone numbers
        guests_with_phone = self.event_guest_ids.filtered(lambda g: g.phone_number)
        
        if not guests_with_phone:
            raise UserError('No guests have phone numbers. Please add phone numbers to guests.')
        
        return {
            'name': 'Send WhatsApp Invitations',
            'type': 'ir.actions.act_window',
            'res_model': 'whatsapp.invitation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_event_id': self.id,
                'default_guest_ids': guests_with_phone.ids,
                'default_message_template': self.invitation_message_template or self._default_invitation_template(),
                'default_invitation_image': self.invitation_image,
                'default_invitation_image_filename': self.invitation_image_filename,
            }
        }
    
    def action_send_whatsapp_attachments(self):
        """Open wizard to send WhatsApp attachments to guests"""
        self.ensure_one()
        
        if not self.event_guest_ids:
            raise UserError('Please add guests to the event before sending attachments.')
        
        # Filter guests with phone numbers
        guests_with_phone = self.event_guest_ids.filtered(lambda g: g.phone_number)
        
        if not guests_with_phone:
            raise UserError('No guests have phone numbers. Please add phone numbers to guests.')
        
        # Get attachments related to this event
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'calendar.event'),
            ('res_id', '=', self.id)
        ])
        
        return {
            'name': 'Send WhatsApp Attachments',
            'type': 'ir.actions.act_window',
            'res_model': 'whatsapp.attachment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_event_id': self.id,
                'default_guest_ids': guests_with_phone.ids,
                'default_attachment_ids': attachments.ids if attachments else [],
            }
        }
    
    def _format_event_date(self):
        """Format event date for message template"""
        self.ensure_one()
        if self.start:
            return self.start.strftime('%A, %B %d, %Y')
        return 'TBD'
    
    def _format_event_time(self):
        """Format event time for message template"""
        self.ensure_one()
        if self.start:
            return self.start.strftime('%I:%M %p')
        return 'TBD'
    
    def _get_venue(self):
        """Get venue information"""
        self.ensure_one()
        if self.location:
            return self.location
        return 'TBD'
    
    def _get_invitation_image_url(self):
        """Get invitation image URL"""
        self.ensure_one()
        # If user provided a direct URL, use it
        if self.invitation_image_url:
            return self.invitation_image_url
        # Otherwise return empty string (placeholder will be removed)
        return ''
    
    def action_send_rsvp_requests(self):
        """Open wizard to send RSVP confirmation requests"""
        self.ensure_one()
        
        if not self.event_guest_ids:
            raise UserError('Please add guests to the event before sending RSVP requests.')
        
        # Filter guests with phone numbers
        guests_with_phone = self.event_guest_ids.filtered(lambda g: g.phone_number)
        
        if not guests_with_phone:
            raise UserError('No guests have phone numbers. Please add phone numbers to guests.')
        
        return {
            'name': 'Send RSVP Requests',
            'type': 'ir.actions.act_window',
            'res_model': 'whatsapp.confirmation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_event_id': self.id,
            }
        }
    
    def action_view_rsvp_stats(self):
        """View RSVP statistics and guest list"""
        self.ensure_one()
        return {
            'name': f'RSVP Status - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'event.guest',
            'view_mode': 'tree,form',
            'domain': [('event_id', '=', self.id)],
            'context': {
                'default_event_id': self.id,
                'search_default_group_by_rsvp_status': 1,
            }
        }


