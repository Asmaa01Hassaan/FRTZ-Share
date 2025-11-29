# -*- coding: utf-8 -*-

from odoo import models, fields,api
from odoo.exceptions import UserError


class EventEvent(models.Model):
    _inherit = 'event.event'

    whatsapp_message_template = fields.Text(
        string='WhatsApp Message Template',
        default=lambda self: self._default_whatsapp_invitation_template(),
        help='Template used when sending WhatsApp invitations. '
             'Use {name}, {event_name}, {date}, {venue}, {time}, {organizer} placeholders.',
    )
    whatsapp_registration_count = fields.Integer(
        string='Registrations with Phone',
        compute='_compute_whatsapp_stats',
    )
    whatsapp_invitation_sent_count = fields.Integer(
        string='WhatsApp Invitations Sent',
        compute='_compute_whatsapp_stats',
    )
    whatsapp_invitation_failed_count = fields.Integer(
        string='WhatsApp Invitations Failed',
        compute='_compute_whatsapp_stats',
    )

    calendar_event_id = fields.Many2one('calendar.event', string="Calendar Event")

    @api.model_create_multi
    def create(self, vals_list):
        events = super(EventEvent, self).create(vals_list)

        for ev in events:
            cal = self.env['calendar.event'].create({
                'name': ev.name,
                'allday': False,
            })
            ev.calendar_event_id = cal.id

        return events

    def _compute_whatsapp_stats(self):
        for event in self:
            registrations = event.registration_ids
            registrations_with_phone = registrations.filtered(
                lambda r: bool(r._format_phone_number_for_whatsapp())
            )
            event.whatsapp_registration_count = len(registrations_with_phone)
            event.whatsapp_invitation_sent_count = len(registrations_with_phone.filtered(
                lambda r: r.whatsapp_invitation_status == 'sent'
            ))
            event.whatsapp_invitation_failed_count = len(registrations_with_phone.filtered(
                lambda r: r.whatsapp_invitation_status == 'failed'
            ))

    def _default_whatsapp_invitation_template(self):
        return """🎉 *Event Invitation* 🎉

Dear {name},

You are invited to *{event_name}*!

📅 Date: {date}
📍 Venue: {venue}
⏰ Time: {time}

We hope to see you there. Please confirm your attendance.

Best regards,
{organizer}"""

    def _format_event_date(self):
        self.ensure_one()
        if self.date_begin:
            localized = fields.Datetime.context_timestamp(self, self.date_begin)
            return localized.strftime('%A, %B %d, %Y')
        return 'TBD'

    def _format_event_time(self):
        self.ensure_one()
        if self.date_begin:
            return fields.Datetime.context_timestamp(self, self.date_begin).strftime('%I:%M %p')
        return 'TBD'

    def _get_venue(self):
        self.ensure_one()
        if self.address_id:
            return self.address_id.display_name
        return 'Online'

    def action_send_whatsapp_invitations(self):
        self.ensure_one()
        registrations_with_phone = self.registration_ids.filtered(
            lambda r: bool(r._format_phone_number_for_whatsapp())
        )
        if not registrations_with_phone:
            raise UserError('No registrations with valid phone numbers were found.')

        return {
            'name': 'Send WhatsApp Invitations',
            'type': 'ir.actions.act_window',
            'res_model': 'event.whatsapp.invitation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_event_id': self.id,
                'default_registration_ids': registrations_with_phone.ids,
                'default_message_template': self.whatsapp_message_template or self._default_whatsapp_invitation_template(),
            },
        }

