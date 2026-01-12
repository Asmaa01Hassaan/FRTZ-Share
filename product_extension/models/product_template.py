# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re


class ProductTemplate(models.Model):
    _inherit = "product.template"

    code = fields.Char(
        string="Code",
        help="Product code identifier"
    )

    subscription_ok = fields.Boolean(
        string='Subscription',
        default=True,
        help="Can be used in subscription orders"
    )

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
        index=True
    )
    internal_reference_new = fields.Char(
        string="Internal Reference"
    )
    cost_method = fields.Selection(
        related='categ_id.property_cost_method',
        readonly=True
    )

    @api.constrains('internal_reference_new', 'categ_id')
    def _check_internal_reference_new(self):
        for product in self:
            cat = product.categ_id
            ref = str(product.internal_reference_new or '')

            if not cat or cat.reference_type == 'manual':
                continue
            if cat.reference_type == 'validation':
                if cat.validation_mode == 'length':
                    if not cat.reference_length:
                        continue
                    if len(ref) > cat.reference_length:
                        raise ValidationError(
                            f"Internal Reference must be exactly "
                            f"{cat.reference_length} characters."
                        )
                if cat.validation_mode in ('type', 'length'):
                    if cat.reference_char_type == 'number':
                        if not ref.isdigit():
                            raise ValidationError(
                                "Internal Reference must contain numbers only."
                            )
                    elif cat.reference_char_type == 'mix':
                        if not (re.search(r'[A-Za-z]', ref) and re.search(r'\d', ref)):
                            raise ValidationError(
                                "Internal Reference must contain both letters and numbers."
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


class ProductTemplateAttributeLine(models.Model):
    _inherit = 'product.template.attribute.line'

    @api.constrains('value_ids', 'attribute_id')
    def _check_valid_values(self):
        for line in self:
            if line.attribute_id.display_type == 'text':
                continue
            if not line.value_ids:
                raise ValidationError(_(
                    "The attribute %(attribute)s must have at least one value for the product %(product)s.",
                    attribute=line.attribute_id.name,
                    product=line.product_tmpl_id.name
                ))

