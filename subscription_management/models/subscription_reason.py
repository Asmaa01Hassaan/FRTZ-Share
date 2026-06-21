# -*- coding: utf-8 -*-
from odoo import fields, models


class SubscriptionReason(models.Model):
    """Shared catalogue of suspension / cancellation / line-pause reasons.

    A single model serves both order-level suspend/cancel and line-level pause;
    `reason_type` filters which reasons are offered in each context.
    """
    _name = 'subscription.reason'
    _description = 'Subscription Suspension/Cancellation Reason'
    _order = 'sequence, name'

    name = fields.Char(string='Reason', required=True, translate=True)
    code = fields.Char(help="Optional code passed to the OSS/provisioning layer.")
    reason_type = fields.Selection(
        [
            ('suspension', 'Temporary Suspension'),
            ('cancellation', 'Permanent Cancellation'),
            ('line_pause', 'Line Pause'),
        ],
        string='Applies To', required=True, default='suspension',
        help="Context where this reason is offered.")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    note = fields.Text(string='Description')
