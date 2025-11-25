# -*- coding: utf-8 -*-

from odoo import models, fields, api


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
    
    event_id = fields.Many2one(
        'calendar.event',
        string='Event',
        required=True,
        ondelete='cascade',
        index=True
    )
    
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
    
    rsvp_status = fields.Selection([
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    ], string='RSVP Status', default='pending')
    
    notes = fields.Text(
        string='Notes',
        help='Additional notes about the guest'
    )
    
    @api.model
    def create(self, vals):
        """Set default invitation status"""
        if 'invitation_status' not in vals:
            vals['invitation_status'] = 'not_sent'
        return super(EventGuest, self).create(vals)
    
    def _format_phone_number(self):
        """Format phone number for WhatsApp (remove non-digits)"""
        self.ensure_one()
        if not self.phone_number:
            return None
        # Remove all non-digit characters
        cleaned = ''.join(filter(str.isdigit, self.phone_number))
        return cleaned if cleaned else None





