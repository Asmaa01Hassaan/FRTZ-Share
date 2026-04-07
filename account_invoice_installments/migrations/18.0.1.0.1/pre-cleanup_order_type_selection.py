def migrate(cr, version):
    """Drop selection metadata for sale.order.order_type after type changed Selection → Char.

    Orphan ir.model.fields.selection rows make Odoo's unlink() call _process_ondelete()
    which expects a Selection field (.ondelete dict); Char has no such attribute → crash.
    """
    cr.execute(
        """
        DELETE FROM ir_model_fields_selection
        WHERE field_id IN (
            SELECT f.id
            FROM ir_model_fields f
            JOIN ir_model m ON m.id = f.model_id
            WHERE m.model = 'sale.order'
              AND f.name = 'order_type'
        )
        """
    )
