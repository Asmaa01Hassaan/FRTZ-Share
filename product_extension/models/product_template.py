# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = "product.template"

    code = fields.Char(
        string="Code",
        help="Product code identifier"
    )

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
        index=True
    )

    @api.depends('name', 'code')
    def _compute_display_name(self):
        """Compute display name as 'CODE NAME' format"""
        for product in self:
            name = product.name or ''
            if product.code:
                name = f"{product.code} {name}"
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
        Override name_search to include code in search
        Allows searching by both name and code
        """
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('code', operator, name)]
        records = self.search(domain + args, limit=limit)
        return records.name_get()

