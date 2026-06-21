from odoo import api, fields, models


class Product(models.Model):
    _inherit = 'product.product'

    is_recurring = fields.Boolean("Recurring")
    subscription_price_ids = fields.One2many(
        comodel_name='product.subscription.pricing',
        inverse_name='product_id',
    )

    def unlink(self):
        self.mapped('subscription_price_ids').unlink()
        return super().unlink()


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_recurring = fields.Boolean("Recurring")
    subscription_price_ids = fields.One2many(
        comodel_name='product.subscription.pricing',
        inverse_name='product_tmpl_id',
        domain=[('product_id', '=', False)],
    )

    def _clear_variant_subscription_pricing(self):
        if not self:
            return
        self.env['product.subscription.pricing'].search([
            ('product_id', 'in', self.mapped('product_variant_ids').ids),
        ]).unlink()

    def _sync_variant_subscription_pricing(self):
        Pricing = self.env['product.subscription.pricing']
        for template in self:
            template._clear_variant_subscription_pricing()
            if not template.is_recurring:
                template.product_variant_ids.is_recurring = False
                continue
            for variant in template.product_variant_ids:
                variant.is_recurring = True
                for line in template.subscription_price_ids:
                    Pricing.create({
                        'period_id': line.period_id.id,
                        'price': line.price,
                        'product_id': variant.id,
                        'product_tmpl_id': template.id,
                    })

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.filtered('is_recurring')._sync_variant_subscription_pricing()
        return records

    def write(self, vals):
        result = super().write(vals)
        if {'is_recurring', 'subscription_price_ids'} & set(vals):
            self._sync_variant_subscription_pricing()
        return result

    def unlink(self):
        self.env['product.subscription.pricing'].search([
            '|',
            ('product_tmpl_id', 'in', self.ids),
            ('product_id', 'in', self.mapped('product_variant_ids').ids),
        ]).unlink()
        return super().unlink()


class ProductSubscriptionPricing(models.Model):
    _name = 'product.subscription.pricing'
    _description = 'product subscription pricing'

    name = fields.Char(string='Name')
    price = fields.Float(string='Price')
    period_id = fields.Many2one(
        comodel_name='product.subscription.period',
        string='Period',
        ondelete='cascade',
    )
    product_tmpl_id = fields.Many2one(
        comodel_name='product.template',
        string='Product Template',
        ondelete='cascade',
        index=True,
    )
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        ondelete='cascade',
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('product_id') and not vals.get('product_tmpl_id'):
                variant = self.env['product.product'].browse(vals['product_id'])
                vals['product_tmpl_id'] = variant.product_tmpl_id.id
        return super().create(vals_list)


class ProductSubscriptionPeriod(models.Model):
    _name = "product.subscription.period"
    _description = "Product Subscription Period"

    name = fields.Char(string='Name')
    duration = fields.Integer(string='Duration')
    unit = fields.Selection(
        string='Unit',
        selection=[('days', 'Days'), ('weeks', 'Weeks'), ('month', 'Months'), ('year', 'Years')],
    )

    price_ids = fields.One2many(
        comodel_name='product.subscription.pricing',
        inverse_name='period_id',
        string='Pricing',
    )

    def unlink(self):
        self.mapped('price_ids').unlink()
        return super().unlink()
