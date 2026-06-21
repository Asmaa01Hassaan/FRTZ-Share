# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class SubscriptionInvoiceWizard(models.TransientModel):
    """Generate a subscription invoice: pick the invoice date and the payment
    terms (defaulted from the subscription order, overridable for this invoice)."""
    _name = 'subscription.invoice.wizard'
    _description = 'Generate Subscription Invoice'

    order_id = fields.Many2one(
        'sale.order', string='Subscription', required=True, readonly=True)
    invoice_date = fields.Date(string='Invoice Date', required=True)
    payment_term_id = fields.Many2one(
        'account.payment.term', string='Payment Terms',
        help="Defaults to the subscription order's payment terms; you can change "
             "it for this invoice.")
    currency_id = fields.Many2one(related='order_id.currency_id', readonly=True)
    company_id = fields.Many2one(related='order_id.company_id', readonly=True)

    def action_generate(self):
        self.ensure_one()
        move = self.order_id._generate_subscription_invoice(
            invoice_date=self.invoice_date,
            payment_term=self.payment_term_id,
        )
        if not move:
            raise UserError(
                _("There is nothing to invoice for this subscription right now."))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoice'),
            'res_model': 'account.move',
            'res_id': move.id,
            'view_mode': 'form',
            'target': 'current',
        }
