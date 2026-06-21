# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # The "Subscription" checkbox itself is `subscription_ok`, provided by
    # product_extension (default True = "can be used in subscription orders").
    # A product becomes a *recurring* item simply by having per-period prices
    # below; products without per-period prices stay one-time.
    subscription_price_ids = fields.One2many(
        'product.subscription.price', 'product_tmpl_id',
        string='Subscription Prices',
        help="Recurring price of this product per billing period "
             "(e.g. Monthly = 100, Yearly = 1000).",
    )
    suspension_fee = fields.Monetary(
        string='Suspension Fee / Cycle', currency_field='currency_id',
        help="Default reduced fee billed per cycle when a recurring line of this "
             "product is paused (item-level suspension).")
    # NOTE: product.product inherits product.template via _inherits, so
    # `subscription_price_ids` is already available (and writable) on
    # product.product through delegation.

    def _get_subscription_price(self, period):
        """Return this product's recurring price for ``period`` (or None)."""
        self.ensure_one()
        if not period:
            return None
        match = self.subscription_price_ids.filtered(
            lambda p: p.period_id == period)[:1]
        return match.price if match else None


class ProductSubscriptionPrice(models.Model):
    _name = 'product.subscription.price'
    _description = 'Product Subscription Price (per billing period)'
    _order = 'product_tmpl_id, price'
    _rec_name = 'period_id'

    product_tmpl_id = fields.Many2one(
        'product.template', string='Product', required=True,
        ondelete='cascade', index=True)
    period_id = fields.Many2one(
        'sale.subscription.period', string='Billing Period', required=True)
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', store=True, readonly=True)
    price = fields.Monetary(
        string='Recurring Price', currency_field='currency_id')

    _sql_constraints = [
        ('uniq_tmpl_period', 'unique(product_tmpl_id, period_id)',
         'There is already a subscription price for this product and this period.'),
    ]
