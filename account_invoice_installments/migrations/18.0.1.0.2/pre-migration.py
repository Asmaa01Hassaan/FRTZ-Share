# -*- coding: utf-8 -*-
"""Remove stale Selection metadata left by the old `order_type` field.

`order_type` on sale.order used to be a Selection (this module) and is now a
Char (sales_order_extension). The leftover ir.model.fields.selection rows make
Odoo's end-of-load cleanup crash with:

    AttributeError: 'Char' object has no attribute 'ondelete'

(in ir.model.fields._process_ondelete, because it reads `field.ondelete` on what
is now a Char field). We delete the orphaned selection rows and their xml-id
records here, before that cleanup runs, so it becomes a no-op.

This is a separate migration version because a previous upgrade attempt already
bumped the module to 18.0.1.0.1 before failing, so the 18.0.1.0.1 migration will
not run again on already-bumped databases.
"""


def migrate(cr, version):
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
