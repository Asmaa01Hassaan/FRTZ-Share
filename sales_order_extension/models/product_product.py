# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.osv import expression


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def _search(self, domain, *args, **kwargs):
        domain = list(domain or [])
        pt = self.env["product.template"]._sale_order_product_type_from_context()
        if pt:
            domain = expression.AND([domain, [("type", "=", pt)]])
        return super()._search(domain, *args, **kwargs)
