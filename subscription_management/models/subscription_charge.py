# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleSubscriptionCharge(models.Model):
    """Variable, unscheduled charge added to a subscription's NEXT invoice.

    Examples: excess international call usage, a temporary extra internet
    package, a one-off service fee.
    """
    _name = 'sale.subscription.charge'
    _description = 'Subscription Ad-hoc Charge'
    _order = 'create_date desc'

    order_id = fields.Many2one(
        'sale.order', string='Subscription', required=True, ondelete='cascade', index=True)
    name = fields.Char(string='Description', required=True)
    product_id = fields.Many2one('product.product', string='Product')
    quantity = fields.Float(string='Quantity', default=1.0)
    price_unit = fields.Float(string='Unit Price')
    tax_ids = fields.Many2many('account.tax', string='Taxes')
    currency_id = fields.Many2one(related='order_id.currency_id', store=True, readonly=True)
    amount_subtotal = fields.Monetary(
        string='Subtotal', compute='_compute_amount_subtotal', store=True, currency_field='currency_id')
    state = fields.Selection(
        [('pending', 'Pending'), ('invoiced', 'Invoiced')], default='pending', copy=False)
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True, copy=False)

    @api.depends('quantity', 'price_unit')
    def _compute_amount_subtotal(self):
        for charge in self:
            charge.amount_subtotal = charge.quantity * charge.price_unit

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            if not self.name:
                self.name = self.product_id.display_name
            if not self.price_unit:
                self.price_unit = self.product_id.lst_price
            if not self.tax_ids:
                self.tax_ids = self.product_id.taxes_id

    def _prepare_invoice_line_vals(self):
        """account.move.line values for billing this charge."""
        self.ensure_one()
        taxes = self.tax_ids
        fiscal_position = self.order_id.fiscal_position_id
        if fiscal_position:
            taxes = fiscal_position.map_tax(taxes)
        return {
            'name': self.name,
            'product_id': self.product_id.id or False,
            'quantity': self.quantity,
            'price_unit': self.price_unit,
            'tax_ids': [(6, 0, taxes.ids)],
        }
