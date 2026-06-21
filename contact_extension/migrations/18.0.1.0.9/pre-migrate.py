"""Remove ir.model metadata left without xml ids after enterprise cleanup."""

def _delete_orphan_ir_model_records(cr):
    cr.execute(
        """
        SELECT m.id
        FROM ir_model m
        WHERE NOT EXISTS (
            SELECT 1
            FROM ir_model_data d
            WHERE d.model = 'ir.model' AND d.res_id = m.id
        )
        """
    )
    orphan_ids = [row[0] for row in cr.fetchall()]
    if not orphan_ids:
        return

    cr.execute("DELETE FROM ir_model_access WHERE model_id = ANY(%s)", (orphan_ids,))
    cr.execute("DELETE FROM ir_rule WHERE model_id = ANY(%s)", (orphan_ids,))
    cr.execute("DELETE FROM ir_model_fields WHERE model_id = ANY(%s)", (orphan_ids,))
    cr.execute("DELETE FROM ir_model WHERE id = ANY(%s)", (orphan_ids,))


def migrate(cr, version):
    _delete_orphan_ir_model_records(cr)
