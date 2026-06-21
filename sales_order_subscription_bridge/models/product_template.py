from odoo import api, models
from odoo.osv import expression


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model
    def _subscription_classification_from_context(self):
        classification = self.env.context.get("restrict_order_classification")
        if classification:
            return classification
        sot = self._resolve_sale_order_type_from_context()
        if sot:
            return sot.order_classification
        return False

    @api.model
    def _search(self, domain, *args, **kwargs):
        domain = list(domain or [])
        if (
            not self.env.context.get("skip_sale_order_product_type_search")
            and not self._domain_targets_explicit_ids(domain)
            and self._in_sale_order_product_context()
            and self._subscription_classification_from_context() == "subscription"
        ):
            domain = expression.AND([domain, [("is_recurring", "=", True)]])
        return super()._search(domain, *args, **kwargs)


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
            and Template._subscription_classification_from_context() == "subscription"
        ):
            domain = expression.AND([domain, [("is_recurring", "=", True)]])
        return super()._search(domain, *args, **kwargs)
