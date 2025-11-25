# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    event_guest_ids = fields.One2many(
        'event.guest',
        'event_id',
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
    
    invitation_message_template = fields.Text(
        string='Invitation Message Template',
        default=lambda self: self._default_invitation_template(),
        help='Message template for WhatsApp invitations. Use {name} for guest name, {event_name} for event name, {date} for event date, {venue} for venue.'
    )
    
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
    
    def _default_invitation_template(self):
        return """🎉 *Wedding Invitation* 🎉

Dear {name},

You are cordially invited to celebrate our special day!

📅 Event: {event_name}
📅 Date: {date}
📍 Venue: {venue}
⏰ Time: {time}

We would be honored to have you join us on this joyous occasion.

Please RSVP at your earliest convenience.

Looking forward to celebrating with you!

With love,
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


