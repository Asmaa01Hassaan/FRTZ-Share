from email.policy import default

from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.attribute'

    display_type = fields.Selection(
        selection_add=[('text', 'Text')],
        ondelete={'text': 'set default'}
    )
    text_value = fields.Text()

    @api.model
    def create(self, vals):
        record = super().create(vals)
        if vals.get('display_type') == 'text' and vals.get('text_value'):
            record._create_text_value()
        return record

    def write(self, vals):
        old_text = self.text_value
        res = super().write(vals)
        for rec in self:
            if rec.display_type == 'text' and (vals.get('text_value') or vals.get('display_type') == 'text'):
                rec._create_text_value(old_text=old_text)
        return res

    def _create_text_value(self, old_text=None):
        """Create or update a matching product.attribute.value and link to attribute lines"""
        self.ensure_one()
        Value = self.env['product.attribute.value']
        if old_text:
            pav = Value.search([
                ('attribute_id', '=', self.id),
                ('name', '=', old_text)
            ], limit=1)
            if pav:
                pav.name = self.text_value
        else:
            pav = Value.search([
                ('attribute_id', '=', self.id),
                ('name', '=', self.text_value)
            ], limit=1)
            if not pav:
                pav = Value.create({
                    'attribute_id': self.id,
                    'name': self.text_value,
                })
        lines = self.env['product.template.attribute.line'].search([
            ('attribute_id', '=', self.id)
        ])
        for line in lines:
            if pav.id not in line.value_ids.ids:
                line.value_ids = [(4, pav.id)]
        lines._update_product_template_attribute_values()
