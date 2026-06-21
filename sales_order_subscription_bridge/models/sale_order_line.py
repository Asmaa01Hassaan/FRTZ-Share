from odoo import api, models, _
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.constrains("product_id", "product_template_id", "order_id")
    def _check_product_subscription_classification(self):
        for line in self:
            if line.display_type or not line.product_id:
                continue
            sot = line.order_id.sale_order_type_id
            if not sot:
                continue
            is_recurring = line.product_id.is_recurring
            if sot.order_classification == "subscription" and not is_recurring:
                raise ValidationError(
                    _(
                        'Product "%(product)s" must be a recurring product for subscription order types.',
                        product=line.product_id.display_name,
                    )
                )
            if sot.order_classification == "sale" and is_recurring:
                raise ValidationError(
                    _(
                        'Recurring product "%(product)s" is only allowed on subscription order types.',
                        product=line.product_id.display_name,
                    )
                )
