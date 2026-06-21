# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountInstallmentPaymentLog(models.Model):
    """Log of payments applied to installments (account.move.installment)."""
    _name = 'account.installment.payment.log'
    _description = 'Installment Payment Log'
    _order = 'create_date desc'

    installment_id = fields.Many2one(
        'account.move.installment',
        string='Installment',
        required=True,
        ondelete='cascade',
        index=True,
    )
    move_id = fields.Many2one(
        'account.move',
        string='Invoice',
        related='installment_id.move_id',
        store=True,
        readonly=True,
    )
    payment_id = fields.Many2one(
        'account.payment',
        string='Payment',
        ondelete='set null',
        index=True,
    )
    paid_amount = fields.Monetary(
        string='Paid Amount',
        currency_field='currency_id',
        required=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='installment_id.currency_id',
        store=True,
        readonly=True,
    )
    action_type = fields.Char(
        string='Action Type',
        help='e.g. action_pay_installments',
    )

    @api.model
    def create_log(self, installment, payment=None, paid_amount=0.0, action_type=None):
        """Create a payment log entry for an installment."""
        if not installment or not paid_amount:
            return False
        return self.create({
            'installment_id': installment.id,
            'payment_id': payment.id if payment else False,
            'paid_amount': paid_amount,
            'action_type': action_type or 'manual',
        })
