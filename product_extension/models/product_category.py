# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductCategory(models.Model):
    _inherit = "product.category"

    code = fields.Char(
        string="Code",
        help="Category code identifier (must be unique)",
        copy=False
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

    validate_length = fields.Boolean(
        string="Validate Length",
        default=False,
        help="Enable length validation for internal references"
    )
    
    validate_type = fields.Boolean(
        string="Validate Type",
        default=False,
        help="Enable character type validation for internal references"
    )

    reference_length = fields.Integer(string="Required Length")

    reference_char_type = fields.Selection([
        ('number', 'Numbers Only'),
        ('mix', 'Mixed'),
    ])

    show_validation_fields = fields.Boolean(
        compute='_compute_show_validation_fields',
        store=False
    )

    reference_sequence_id = fields.Many2one(
        'ir.sequence',
        string="Reference Sequence",
        help="Sequence to use for automatic reference generation. "
             "If not set, the default product reference sequence will be used."
    )

    # Boolean fields for allowed product types (like validation checkboxes)
    allow_consu = fields.Boolean(
        string="Allow Goods",
        default=False,
        help="Allow 'Goods' product type in this category"
    )
    
    allow_service = fields.Boolean(
        string="Allow Service",
        default=False,
        help="Allow 'Service' product type in this category"
    )
    
    allow_combo = fields.Boolean(
        string="Allow Combo",
        default=False,
        help="Allow 'Combo' product type in this category"
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

    def write(self, vals):
        """Override write to strip code and ensure uniqueness"""
        if 'code' in vals and vals['code']:
            vals['code'] = vals['code'].strip()
        return super().write(vals)
    
    @api.model
    def create(self, vals_list):
        """Override create to strip code"""
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        for vals in vals_list:
            if 'code' in vals and vals.get('code'):
                vals['code'] = vals['code'].strip()
        return super().create(vals_list)
    
    @api.constrains('code')
    def _check_unique_code(self):
        """Ensure category code is unique (case-insensitive)"""
        for category in self:
            if category.code:
                # Search for other categories with the same code (case-insensitive)
                duplicate = self.search([
                    ('code', '=ilike', category.code),
                    ('id', '!=', category.id)
                ], limit=1)
                if duplicate:
                    raise ValidationError(
                        _("Category code '%s' already exists in category '%s'. Please use a unique code.") % (
                            category.code, duplicate.name
                        )
                    )

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

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Category code must be unique!')
    ]

