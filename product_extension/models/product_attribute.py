from email.policy import default

from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.attribute'

    display_type = fields.Selection(
        selection_add=[('text', 'Text')],
        ondelete={'text': 'set default'}
    )

    @api.model
    def create(self, vals):
        if vals.get('display_type') == 'text':
            vals['create_variant'] = 'no_variant'
        return super().create(vals)

    def write(self, vals):
        if vals.get('display_type') == 'text':
            vals['create_variant'] = 'no_variant'
        return super().write(vals)