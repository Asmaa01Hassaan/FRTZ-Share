# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_open_reschedule_wizard(self):
        """Open the installment reschedule wizard for this invoice."""
        self.ensure_one()
        unpaid = self.installment_ids.filtered(
            lambda i: i.state in ('draft', 'due', 'partial', 'overdue')
            and i.amount_residual > 0
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reschedule Installments'),
            'res_model': 'installment.reschedule.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_move_id': self.id,
                'default_partner_id': self.partner_id.id,
                'active_installment_ids': unpaid.ids,
            },
        }
