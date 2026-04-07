def migrate(cr, version):
    """Idempotent cleanup; see 18.0.1.0.1/pre-cleanup_order_type_selection.py."""
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
