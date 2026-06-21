# -*- coding: utf-8 -*-
from odoo import fields, models


class SubscriptionLifecycleWizard(models.TransientModel):
    """Suspend (temporary) or Cancel (permanent) a subscription WITH a reason."""
    _name = 'subscription.lifecycle.wizard'
    _description = 'Suspend / Cancel Subscription'

    order_id = fields.Many2one('sale.order', string='Subscription', required=True, readonly=True)
    mode = fields.Selection(
        [('suspend', 'Suspend'), ('cancel', 'Cancel')], required=True, readonly=True)
    reason_id = fields.Many2one(
        'subscription.reason', string='Reason', required=True,
        domain="[('reason_type', '=', mode == 'suspend' and 'suspension' or 'cancellation')]")
    note = fields.Text(string='Note')

    def action_confirm(self):
        self.ensure_one()
        if self.mode == 'suspend':
            self.order_id.action_suspend_subscription(reason_id=self.reason_id.id, note=self.note)
        else:
            self.order_id.action_cancel_subscription(reason_id=self.reason_id.id, note=self.note)
        return {'type': 'ir.actions.act_window_close'}
