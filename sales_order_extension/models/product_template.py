# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.osv import expression


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model
    def _sale_order_product_type_from_context(self):
        """Resolve consu/service/combo from SO context (no nested fields in XML — use order_id / sale_order_type_id)."""
        pt = self.env.context.get("restrict_order_product_type")
        if pt:
            return pt
        order_id = self.env.context.get("order_id")
        if order_id:
            order = self.env["sale.order"].browse(order_id)
            if order.exists() and order.sale_order_type_id:
                return order.sale_order_type_id.product_type
        sot_id = self.env.context.get("sale_order_type_id")
        if sot_id:
            if isinstance(sot_id, (list, tuple)):
                sot_id = sot_id[0]
            sot = self.env["sale.order.type"].browse(sot_id)
            if sot.exists():
                return sot.product_type
        return False

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
    def _search(self, domain, *args, **kwargs):
        domain = list(domain or [])
        pt = self._sale_order_product_type_from_context()
        if pt:
            domain = expression.AND([domain, [("type", "=", pt)]])
        return super()._search(domain, *args, **kwargs)
