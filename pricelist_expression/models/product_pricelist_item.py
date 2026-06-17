# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import ValidationError
import logging
import math
import re
from .product_pricelist_item_variable import ALLOWED_EXPRESSION_MODELS, BUILTIN_EXPRESSION_NAMES

_logger = logging.getLogger(__name__)

class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    compute_price = fields.Selection(
        selection_add=[('expression', 'Expression')],
        ondelete={'expression': 'set default'},
    )

    price_expression = fields.Char(
        string="Expression",
        help=(
            "Python expression that returns the final unit price.\n"
            "Available variables:\n"
            "price → base price\n"
            "cost → standard cost\n"
            "purchase_price → purchase price (same as cost)\n"
            "qty → quantity\n"
            "installment_num → installment count (header or line, by scope)\n"
            "first_payment → first payment value (header or line, by scope)\n"
            "ceil(x) → round up to next integer\n"
            "round(x, n) → normal rounding\n"
            "Plus any custom variables configured below."
        ),
    )

    expression_model_id = fields.Many2one(
        'ir.model',
        string='Variable Model',
        domain=[('model', 'in', list(ALLOWED_EXPRESSION_MODELS))],
        help='Default model when adding custom expression variables.',
    )
    expression_variable_ids = fields.One2many(
        'product.pricelist.item.variable',
        'item_id',
        string='Custom Variables',
    )
    expression_custom_variable_help = fields.Html(
        string='Custom Variables Help',
        compute='_compute_expression_custom_variable_help',
        sanitize=False,
    )

    payment_type = fields.Selection(
        [
            ('immediate', _('Immediate Payment')),
            ('regular', _('Regular Installments')),
            ('irregular', _('Irregular Installments')),
        ],
        string=_("Payment plan"),
        default=False,
        help=_("Leave empty to apply this pricelist rule to all payment plans.")
    )

    @api.depends('expression_variable_ids', 'expression_variable_ids.variable_name', 'expression_variable_ids.field_id')
    def _compute_expression_custom_variable_help(self):
        for item in self:
            if not item.expression_variable_ids:
                item.expression_custom_variable_help = False
                continue
            rows = []
            for var in item.expression_variable_ids:
                label = var.field_id.field_description or var.field_id.name
                rows.append(
                    '<li><code>%s</code> - %s (<i>%s</i> / %s)</li>'
                    % (var.variable_name, label, var.model_id.name, var.field_id.name)
                )
            item.expression_custom_variable_help = (
                '<ul class="mb-0 mt-2" style="list-style-type: disc; padding-left: 20px;">'
                + ''.join(rows)
                + '</ul>'
            )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'expression_model_id' in fields_list and not res.get('expression_model_id'):
            model = self.env['ir.model'].sudo().search([('model', '=', 'sale.order.line')], limit=1)
            if model:
                res['expression_model_id'] = model.id
        return res

    def _get_custom_expression_env(self):
        """Merge configured field variables into the expression environment."""
        self.ensure_one()
        sources = self.env.context.get('pricelist_expression_sources') or {}
        env_vars = {}
        for var in self.expression_variable_ids:
            env_vars[var.variable_name] = var._resolve_value(sources)
        return env_vars

    def _compute_price(self, *args, **kwargs):
        """Compute price using expression if configured"""
        base_price = super()._compute_price(*args, **kwargs)

        product = args[0] if len(args) >= 1 else kwargs.get("product")
        quantity = args[1] if len(args) >= 2 else kwargs.get("quantity", 1.0)

        if self.compute_price == "expression" and self.price_expression:
            try:
                # Get product cost and purchase price safely
                cost = 0.0
                purchase_price = 0.0
                if product:
                    cost = float(getattr(product, "standard_price", 0.0) or 0.0)
                    purchase_price = cost  # purchase_price is same as standard_price (cost)
                
                # Helper function for conditional expressions (SQL-style: if(condition, true_value, false_value))
                def iff(condition, true_value, false_value):
                    """Conditional expression: returns true_value if condition is True, else false_value"""
                    return float(true_value) if condition else float(false_value)
                
                # Preprocess expression: replace if( with iff( to avoid Python keyword conflict
                # This allows users to write if(condition, true, false) which gets converted to iff(condition, true, false)
                expression = str(self.price_expression).strip()
                # Replace if( with iff( using word boundary to avoid replacing "if " or other variations
                expression = re.sub(r'\bif\s*\(', 'iff(', expression)
                
                env = {
                    "price": float(base_price or 0.0),
                    "cost": cost,
                    "purchase_price": purchase_price,  # Purchase price (same as cost/standard_price)
                    "qty": float(quantity or 0.0),
                    "installment_num": float(self.env.context.get("installment_num", 0.0) or 0.0),
                    "first_payment": float(self.env.context.get("first_payment", 0.0) or 0.0),
                    "round": round,
                    "ceil": math.ceil,
                    "iff": iff,  # Conditional function: iff(condition, true_value, false_value)
                }
                env.update(self._get_custom_expression_env())
                
                new_price = float(safe_eval(expression, env, nocopy=True))
                _logger.debug(f"Expression pricing: {self.price_expression} -> {new_price} (processed: {expression})")
                return new_price
                
            except Exception as e:
                _logger.error(f"Error evaluating price expression '{self.price_expression}': {e}")
                # Return base price as fallback
                return base_price

        return base_price
