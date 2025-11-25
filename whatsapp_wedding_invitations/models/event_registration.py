# -*- coding: utf-8 -*-

from odoo import models, fields


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    whatsapp_invitation_status = fields.Selection(
        [
            ('not_sent', 'Not Sent'),
            ('sent', 'Sent'),
            ('failed', 'Failed'),
        ],
        string='WhatsApp Invitation Status',
        default='not_sent',
        tracking=True,
    )
    whatsapp_invitation_sent_date = fields.Datetime(
        string='WhatsApp Invitation Sent',
        tracking=True,
    )
    whatsapp_invitation_error = fields.Text(
        string='WhatsApp Error',
    )
    whatsapp_message_id = fields.Char(
        string='WhatsApp Message ID',
    )

    def _format_phone_number_for_whatsapp(self):
        """Return digits-only phone number for WhatsApp."""
        self.ensure_one()
        phone_candidates = [
            self.mobile,
            self.phone,
            self.partner_id.mobile if self.partner_id else False,
            self.partner_id.phone if self.partner_id else False,
        ]
        for number in phone_candidates:
            if not number:
                continue
            cleaned = ''.join(filter(str.isdigit, number))
            if cleaned:
                return cleaned
        return False


