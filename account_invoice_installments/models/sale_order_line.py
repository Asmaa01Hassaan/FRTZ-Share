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
        pt = (
            self.order_id.sale_order_type_id.product_type
            if self.order_id and self.order_id.sale_order_type_id
            else False
        )
        if pt:
            domain.append(("type", "=", pt))
        return {"domain": {"product_id": domain, "product_template_id": domain}}

    @api.constrains("product_id", "product_template_id", "order_id")
    def _check_product_matches_order_product_type(self):
        for line in self:
            if line.display_type or not line.order_id:
                continue
            sot = line.order_id.sale_order_type_id
            opt = sot.product_type if sot else False
            if not opt:
                continue
            tmpl_type = False
            if line.product_id:
                tmpl_type = line.product_id.type
            elif line.product_template_id:
                tmpl_type = line.product_template_id.type
            if tmpl_type and tmpl_type != opt:
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
