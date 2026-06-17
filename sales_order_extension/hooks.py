def post_init_hook(env):
    """Back-fill sequence_prefix and sync menus/sequences for existing sale order types."""
    types = env["sale.order.type"].search([])
    for rec in types:
        if not rec.sequence_prefix:
            rec.sequence_prefix = rec._suggest_sequence_prefix(rec.name)
    types._ensure_sequence()
    types._ensure_dynamic_menu_and_action()
