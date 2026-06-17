# -*- coding: utf-8 -*-
import ast

from odoo import api, models
from odoo.osv import expression


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model
    def _normalize_context_id(self, value):
        if isinstance(value, int):
            return value
        if isinstance(value, (list, tuple)):
            return value[0] if value else False
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return False
            if value.isdigit():
                return int(value)
            try:
                parsed = ast.literal_eval(value)
            except (SyntaxError, ValueError):
                return False
            return self._normalize_context_id(parsed)
        return False

    @api.model
    def _normalize_context_id_list(self, value):
        if value in (None, False):
            return []
        if isinstance(value, int):
            return [value]
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return []
            try:
                parsed = ast.literal_eval(value)
            except (SyntaxError, ValueError):
                if value.isdigit():
                    return [int(value)]
                return [int(part) for part in value.split(",") if part.strip().isdigit()]
            return self._normalize_context_id_list(parsed)
        if isinstance(value, (list, tuple, set)):
            ids = []
            for item in value:
                normalized = self._normalize_context_id(item)
                if normalized:
                    ids.append(normalized)
            return ids
        normalized = self._normalize_context_id(value)
        return [normalized] if normalized else []

    @api.model
    def _resolve_sale_order_type_from_context(self):
        ctx = self.env.context
        sot_id = self._normalize_context_id(ctx.get("sale_order_type_id"))
        if not sot_id:
            sot_id = self._normalize_context_id(ctx.get("default_sale_order_type_id"))
        if not sot_id:
            order_id = self._normalize_context_id(ctx.get("order_id"))
            if order_id:
                order = self.env["sale.order"].browse(order_id)
                if order.exists() and order.sale_order_type_id:
                    return order.sale_order_type_id
        if sot_id:
            sot = self.env["sale.order.type"].browse(sot_id)
            if sot.exists():
                return sot
        return self.env["sale.order.type"]

    @api.model
    def _in_sale_order_product_context(self):
        ctx = self.env.context
        if ctx.get("restrict_order_product_type") or ctx.get("restrict_order_product_category_ids"):
            return True
        if ctx.get("sale_order_type_id") or ctx.get("default_sale_order_type_id") or ctx.get("order_id"):
            return True
        return False

    @api.model
    def _sale_order_product_type_from_context(self):
        """Resolve consu/service/combo from SO context (no nested fields in XML — use order_id / sale_order_type_id)."""
        pt = self.env.context.get("restrict_order_product_type")
        if pt:
            return pt
        sot = self._resolve_sale_order_type_from_context()
        if sot:
            return sot.product_type
        return False

    @api.model
    def _sale_order_product_categories_from_context(self):
        """Resolve allowed product category ids from SO context."""
        cat_ids = self._normalize_context_id_list(
            self.env.context.get("restrict_order_product_category_ids")
        )
        if cat_ids:
            return cat_ids
        sot = self._resolve_sale_order_type_from_context()
        if sot and sot.product_category_ids:
            return sot.product_category_ids.ids
        return []

    @api.model
    def _sale_order_allowed_category_ids(self):
        cat_ids = self._sale_order_product_categories_from_context()
        if not cat_ids:
            return []
        return self.env["product.category"].search([("id", "child_of", cat_ids)]).ids

    @api.model
    def _sale_order_product_category_domain(self, categ_field="categ_id"):
        allowed = self._sale_order_allowed_category_ids()
        if not allowed:
            if self._sale_order_product_categories_from_context():
                return [(categ_field, "=", False)]
            return []
        return [(categ_field, "in", allowed)]

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        lock = self._sale_order_product_type_from_context()
        if lock and "type" in fields_list:
            res["type"] = lock
        return res

    @api.model_create_multi
    def create(self, vals_list):
        lock = self._sale_order_product_type_from_context()
        if lock:
            vals_list = [{**vals, "type": lock} for vals in vals_list]
        return super().create(vals_list)

    def write(self, vals):
        lock = self._sale_order_product_type_from_context()
        if lock and "type" in vals:
            vals = dict(vals)
            vals["type"] = lock
        return super().write(vals)

    @api.model
    def _domain_targets_explicit_ids(self, domain):
        """Skip SO type filter when resolving known records (fetch, onchange lines, etc.)."""
        for token in domain or []:
            if token in ("|", "&", "!"):
                continue
            if isinstance(token, (list, tuple)) and len(token) == 3 and token[0] == "id":
                return True
        return False

    @api.model
    def _search(self, domain, *args, **kwargs):
        domain = list(domain or [])
        if (
            not self.env.context.get("skip_sale_order_product_type_search")
            and not self._domain_targets_explicit_ids(domain)
            and self._in_sale_order_product_context()
        ):
            pt = self._sale_order_product_type_from_context()
            if pt:
                domain = expression.AND([domain, [("type", "=", pt)]])
            cat_domain = self._sale_order_product_category_domain()
            if cat_domain:
                domain = expression.AND([domain, cat_domain])
        return super()._search(domain, *args, **kwargs)
