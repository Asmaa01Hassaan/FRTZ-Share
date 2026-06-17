# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

ALLOWED_EXPRESSION_MODELS = (
    'sale.order.line',
    'sale.order',
    'sale.order.installment',
    'product.product',
    'account.move.line',
    'account.move',
    'account.move.installment',
)

BUILTIN_EXPRESSION_NAMES = frozenset({
    'price', 'cost', 'purchase_price', 'qty', 'installment_num', 'first_payment',
    'round', 'ceil', 'iff', 'if', 'True', 'False', 'None',
})

NUMERIC_FIELD_TYPES = ('integer', 'float', 'monetary', 'boolean')


class ProductPricelistItemVariable(models.Model):
    _name = 'product.pricelist.item.variable'
    _description = 'Pricelist Expression Variable'
    _order = 'sequence, id'

    item_id = fields.Many2one(
        'product.pricelist.item',
        string='Pricelist Rule',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        required=True,
        ondelete='cascade',
        domain=[('model', 'in', list(ALLOWED_EXPRESSION_MODELS))],
    )
    field_id = fields.Many2one(
        'ir.model.fields',
        string='Field',
        required=True,
        ondelete='cascade',
        domain="[('model_id', '=', model_id), ('ttype', 'in', %s)]" % (list(NUMERIC_FIELD_TYPES),),
    )
    variable_name = fields.Char(
        string='Variable Name',
        required=True,
        help='Name used in the expression, e.g. my_field → price + my_field',
    )

    @api.onchange('model_id')
    def _onchange_model_id(self):
        self.field_id = False

    @api.onchange('field_id')
    def _onchange_field_id(self):
        if self.field_id and not self.variable_name:
            self.variable_name = self.field_id.name

    @api.constrains('variable_name', 'item_id')
    def _check_variable_name(self):
        ident = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
        for rec in self:
            name = (rec.variable_name or '').strip()
            if not name or not ident.match(name):
                raise ValidationError(_('Variable name must be a valid identifier (letters, digits, underscore).'))
            if name in BUILTIN_EXPRESSION_NAMES:
                raise ValidationError(_('Variable name "%s" is reserved.', name))
            duplicates = rec.item_id.expression_variable_ids.filtered(
                lambda v: v.variable_name == name and v.id != rec.id
            )
            if duplicates:
                raise ValidationError(_('Variable name "%s" is already used on this rule.', name))

    @api.constrains('field_id', 'model_id')
    def _check_field_matches_model(self):
        for rec in self:
            if rec.field_id and rec.model_id and rec.field_id.model_id != rec.model_id:
                raise ValidationError(_('Field must belong to the selected model.'))

    def _to_float(self, value):
        if isinstance(value, bool):
            return 1.0 if value else 0.0
        if value in (None, False):
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _resolve_value(self, sources):
        """Resolve this variable from pre-built source field maps."""
        self.ensure_one()
        model_name = self.model_id.model
        field_name = self.field_id.name
        model_sources = sources.get(model_name) or {}
        if field_name not in model_sources:
            return 0.0
        return self._to_float(model_sources[field_name])
