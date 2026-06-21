# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SubscriptionStateLog(models.Model):
    """Immutable audit trail of every subscription state change, at order level
    (activate/suspend/resume/cancel/close) and line level (pause/resume)."""
    _name = 'subscription.state.log'
    _description = 'Subscription State-Change Log'
    _order = 'date desc, id desc'

    order_id = fields.Many2one(
        'sale.order', string='Subscription', required=True, ondelete='cascade', index=True)
    partner_id = fields.Many2one(
        related='order_id.partner_id', string='Customer', store=True, index=True)
    order_line_id = fields.Many2one(
        'sale.order.line', string='Line', ondelete='cascade',
        help="Set for line-level pause/resume events; empty for order-level events.")
    product_id = fields.Many2one(related='order_line_id.product_id', store=True)
    action = fields.Selection(
        [
            ('activate', 'Activated'),
            ('suspend', 'Suspended'),
            ('resume', 'Resumed'),
            ('cancel', 'Cancelled'),
            ('close', 'Closed'),
            ('pause_line', 'Line Paused'),
            ('resume_line', 'Line Resumed'),
        ],
        string='Action', required=True)
    reason_id = fields.Many2one('subscription.reason', string='Reason')
    note = fields.Text(string='Note')
    user_id = fields.Many2one(
        'res.users', string='Done By', default=lambda self: self.env.user, readonly=True)
    date = fields.Datetime(string='Date', default=fields.Datetime.now, readonly=True)
    currency_id = fields.Many2one(related='order_id.currency_id')
    fee_amount = fields.Monetary(
        string='Reduced Fee / Cycle', currency_field='currency_id',
        help="Reduced suspension fee billed per cycle, for line pauses that keep billing.")
