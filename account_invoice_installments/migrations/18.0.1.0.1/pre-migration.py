# -*- coding: utf-8 -*-
"""Preserve legacy `order_type` data when renaming it to `installment_order_type`.

Context: `order_type` (a Selection on sale.order) was renamed to
`installment_order_type` to remove a hard field-name collision with
sales_order_extension's `order_type` Char. This pre-migration copies the existing
values into the new column BEFORE the ORM processes the renamed field, so no data
is lost.

It is defensive: only recognised selection keys are copied, so any free-text/Char
data that may have leaked into the shared `order_type` column (from the colliding
definition) is ignored rather than written into the Selection field.
"""


def migrate(cr, version):
    # Nothing to do if the old column is gone (fresh install / already migrated).
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'sale_order' AND column_name = 'order_type'
        """
    )
    if not cr.fetchone():
        return

    cr.execute(
        """
        ALTER TABLE sale_order
        ADD COLUMN IF NOT EXISTS installment_order_type varchar
        """
    )

    cr.execute(
        """
        UPDATE sale_order
        SET installment_order_type = order_type
        WHERE order_type IN ('standard', 'custom', 'wholesale', 'subscription')
          AND installment_order_type IS NULL
        """
    )

    # `order_type` is now a Char (owned by sales_order_extension), but the old
    # Selection left behind ir.model.fields.selection rows on sale.order.order_type.
    # At the end of loading Odoo tries to clean those up and reads `field.ondelete`,
    # which crashes with "'Char' object has no attribute 'ondelete'". Remove the
    # stale Selection metadata (and its xml-id rows) here so that cleanup is a no-op.
    cr.execute(
        """
        DELETE FROM ir_model_data
        WHERE model = 'ir.model.fields.selection'
          AND res_id IN (
            SELECT s.id
            FROM ir_model_fields_selection s
            JOIN ir_model_fields f ON f.id = s.field_id
            WHERE f.model = 'sale.order' AND f.name = 'order_type'
          )
        """
    )
    cr.execute(
        """
        DELETE FROM ir_model_fields_selection
        WHERE field_id IN (
            SELECT id FROM ir_model_fields
            WHERE model = 'sale.order' AND name = 'order_type'
        )
        """
    )
