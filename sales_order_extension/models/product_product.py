# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.osv import expression


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model
    def _search(self, domain, *args, **kwargs):
        domain = list(domain or [])
        Template = self.env["product.template"]
        if (
            not self.env.context.get("skip_sale_order_product_type_search")
            and not Template._domain_targets_explicit_ids(domain)
            and Template._in_sale_order_product_context()
        ):
            pt = Template._sale_order_product_type_from_context()
            if pt:
                domain = expression.AND([domain, [("type", "=", pt)]])
            cat_domain = Template._sale_order_product_category_domain(
                categ_field="product_tmpl_id.categ_id"
            )
            if cat_domain:
                domain = expression.AND([domain, cat_domain])
        return super()._search(domain, *args, **kwargs)
