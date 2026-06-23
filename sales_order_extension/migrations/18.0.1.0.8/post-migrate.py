# -*- coding: utf-8 -*-
def migrate(cr, version):
    """Drop the redundant default search filter (the starred facet) and the
    'search_default_sale_order_type_id' context from every dynamic sale order
    type screen. The action domain already restricts records to the type, so the
    filter/facet only cluttered the search bar. Re-sync via the model so existing
    types pick up the new action context + filter cleanup.
    """
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    types = env["sale.order.type"].search([])
    if types:
        types._ensure_dynamic_menu_and_action()
