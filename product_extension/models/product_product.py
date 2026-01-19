# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ProductProduct(models.Model):
    _inherit = "product.product"

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
        index=True
    )

    @api.depends('name', 'product_tmpl_id.internal_reference_new', 'default_code')
    def _compute_display_name(self):
        """Compute display name as 'INTERNAL_REFERENCE NAME' format using template internal_reference_new or default_code"""
        for product in self:
            name = product.name or ''
            # Use template internal_reference_new if available, otherwise use default_code
            ref = product.product_tmpl_id.internal_reference_new or product.default_code
            if ref:
                name = f"{ref} {name}"
            product.display_name = name

    def name_get(self):
        """Override to return formatted display name"""
        result = []
        for product in self:
            result.append((product.id, product.display_name or product.name))
        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """
        Override name_search to include internal_reference_new and default_code in search
        Allows searching by name, template internal_reference_new, or default_code
        """
        args = args or []
        domain = []
        if name:
            domain = ['|', '|', ('name', operator, name), ('product_tmpl_id.internal_reference_new', operator, name), ('default_code', operator, name)]
        records = self.search(domain + args, limit=limit)
        return records.name_get()

