# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AccountInstallmentPaymentLog(models.Model):
    _inherit = 'account.installment.payment.log'

    name = fields.Char(
        string='Reference',
        readonly=True,
        copy=False,
        default='New',
    )
    date = fields.Date(
        string='Payment Date',
        default=fields.Date.today,
    )
    display_reference = fields.Char(
        string='Installment Ref.',
        related='installment_id.display_reference',
        store=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        related='installment_id.partner_id',
        store=True,
        readonly=True,
    )
    amount_before = fields.Monetary(
        string='Paid Before',
        currency_field='currency_id',
        readonly=True,
        help='Cumulative paid amount before this payment',
    )
    amount_after = fields.Monetary(
        string='Paid After',
        currency_field='currency_id',
        readonly=True,
        help='Cumulative paid amount after this payment',
    )
    state_before = fields.Selection(
        [
            ('draft', 'Draft'),
            ('due', 'Due'),
            ('paid', 'Paid'),
            ('partial', 'Partially Paid'),
            ('overdue', 'Overdue'),
        ],
        string='Status Before',
        readonly=True,
    )
    state_after = fields.Selection(
        [
            ('draft', 'Draft'),
            ('due', 'Due'),
            ('paid', 'Paid'),
            ('partial', 'Partially Paid'),
            ('overdue', 'Overdue'),
        ],
        string='Status After',
        readonly=True,
    )
    notes = fields.Text(string='Notes')

    @api.model
    def create(self, vals):
        if isinstance(vals, dict):
            vals_list = [vals]
        else:
            vals_list = vals
        for v in vals_list:
            if v.get('name', 'New') == 'New':
                v['name'] = self.env['ir.sequence'].next_by_code(
                    'account.installment.payment.log'
                ) or 'New'
        return super().create(vals if not isinstance(vals, dict) else vals_list[0])

    def _derive_state(self, installment, amount_paid):
        """Determine what state an installment would have with the given amount_paid."""
        residual = (installment.amount_total or 0.0) - amount_paid
        today = fields.Date.today()
        if residual <= 0:
            return 'paid'
        elif amount_paid > 0:
            return 'partial'
        elif installment.date_due and installment.date_due < today:
            return 'overdue'
        elif installment.date_due and installment.date_due >= today:
            return 'due'
        return 'draft'

    @api.model
    def create_log(self, installment, payment=None, paid_amount=0.0, action_type=None):
        """Enhanced log creation that captures before/after state."""
        if not installment or not paid_amount:
            return False

        amount_after = installment.amount_paid or 0.0
        amount_before = amount_after - paid_amount
        if amount_before < 0:
            amount_before = 0.0

        state_before = self._derive_state(installment, amount_before)
        state_after = self._derive_state(installment, amount_after)

        return self.create({
            'installment_id': installment.id,
            'payment_id': payment.id if payment else False,
            'paid_amount': paid_amount,
            'action_type': action_type or 'manual',
            'date': fields.Date.today(),
            'amount_before': amount_before,
            'amount_after': amount_after,
            'state_before': state_before,
            'state_after': state_after,
        })
