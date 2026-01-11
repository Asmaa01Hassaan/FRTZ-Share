# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ProductCategory(models.Model):
    _inherit = "product.category"

    code = fields.Char(
        string="Code",
        help="Category code identifier"
    )

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
        index=True
    )
    reference_type = fields.Selection([
        ('manual', 'Manual'),
        ('validation', 'Validation'),
        ('automatic', 'Automatic'),
    ], default='manual')

    validation_mode = fields.Selection([
        ('length', 'Length'),
        ('type', 'Type'),
    ])

    reference_length = fields.Integer(string="Required Length")

    reference_char_type = fields.Selection([
        ('number', 'Numbers Only'),
        ('mix', 'Mixed'),
    ])

    show_validation_fields = fields.Boolean(
        compute='_compute_show_validation_fields',
        store=False
    )

    @api.depends('reference_type')
    def _compute_show_validation_fields(self):
        for cat in self:
            cat.show_validation_fields = cat.reference_type == 'validation'

    @api.depends('name', 'code')
    def _compute_display_name(self):
        """Compute display name as 'CODE NAME' format"""
        for category in self:
            name = category.name or ''
            if category.code:
                name = f"{category.code} {name}"
            category.display_name = name

    def name_get(self):
        """Override to return formatted display name"""
        result = []
        for category in self:
            result.append((category.id, category.display_name or category.name))
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

