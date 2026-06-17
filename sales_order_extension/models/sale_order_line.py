# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    so_order_product_type = fields.Selection(
        related="order_id.sale_order_type_id.product_type",
        readonly=True,
    )

    @api.onchange("order_id")
    def _onchange_order_id_product_domain(self):
        return self._product_id_domain_onchange()

    @api.onchange("so_order_product_type")
    def _onchange_so_order_product_type_domain(self):
        return self._product_id_domain_onchange()

    def _product_id_domain_onchange(self):
        domain = [("sale_ok", "=", True)]
        sot = self.order_id.sale_order_type_id if self.order_id else False
        if sot and sot.product_type:
            domain.append(("type", "=", sot.product_type))
        if sot:
            cat_domain = sot._product_category_domain()
            if cat_domain:
                domain.extend(cat_domain)
        return {"domain": {"product_id": domain, "product_template_id": domain}}

    @api.constrains("product_id", "product_template_id", "order_id")
    def _check_product_matches_order_product_type(self):
        for line in self:
            if line.display_type or not line.order_id:
                continue
            sot = line.order_id.sale_order_type_id
            if not sot:
                continue
            opt = sot.product_type
            tmpl_type = False
            categ = False
            if line.product_id:
                tmpl_type = line.product_id.type
                categ = line.product_id.categ_id
            elif line.product_template_id:
                tmpl_type = line.product_template_id.type
                categ = line.product_template_id.categ_id
            if opt and tmpl_type and tmpl_type != opt:
                name = (
                    line.product_id.display_name
                    if line.product_id
                    else line.product_template_id.display_name
                )
                raise ValidationError(
                    _(
                        'Product "%(prod)s" must be of the same type as this order (expected: %(expected)s).',
                        prod=name,
                        expected=opt,
                    )
                )
            if sot.product_category_ids and not sot._is_category_allowed(categ):
                name = (
                    line.product_id.display_name
                    if line.product_id
                    else line.product_template_id.display_name
                )
                allowed = ", ".join(sot.product_category_ids.mapped("display_name"))
                raise ValidationError(
                    _(
                        'Product "%(prod)s" is not in an allowed category for this order type. '
                        "Allowed categories: %(allowed)s.",
                        prod=name,
                        allowed=allowed,
                    )
                )
