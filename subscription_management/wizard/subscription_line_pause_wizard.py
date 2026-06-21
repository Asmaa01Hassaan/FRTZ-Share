# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SubscriptionLinePauseWizard(models.TransientModel):
    """Pause a single recurring line WITH a reason (and optional reduced fee)."""
    _name = 'subscription.line.pause.wizard'
    _description = 'Pause Subscription Line'

    line_id = fields.Many2one('sale.order.line', string='Line', required=True, readonly=True)
    product_id = fields.Many2one(related='line_id.product_id', readonly=True)
    reason_id = fields.Many2one(
        'subscription.reason', string='Reason', required=True,
        domain="[('reason_type', '=', 'line_pause')]")
    note = fields.Char(string='Note')
    planned_resume_date = fields.Date(string='Planned Resume Date')
    charge_suspension_fee = fields.Boolean(string='Charge Reduced Fee While Paused')
    suspension_fee_amount = fields.Monetary(
        string='Suspension Fee / Cycle', currency_field='currency_id')
    currency_id = fields.Many2one(related='line_id.order_id.currency_id', readonly=True)

    @api.onchange('charge_suspension_fee')
    def _onchange_charge_fee(self):
        if self.charge_suspension_fee and not self.suspension_fee_amount:
            self.suspension_fee_amount = self.product_id.suspension_fee

    def action_confirm(self):
        self.ensure_one()
        self.line_id.action_pause_subscription_line(
            reason_id=self.reason_id.id,
            note=self.note,
            planned_resume_date=self.planned_resume_date,
            charge_fee=self.charge_suspension_fee,
            fee_amount=self.suspension_fee_amount,
        )
        return {'type': 'ir.actions.act_window_close'}
