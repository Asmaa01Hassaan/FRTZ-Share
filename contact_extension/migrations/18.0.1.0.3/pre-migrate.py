import json
import re


def _clean_arch_db(cr, model, pattern, arch_filter):
    cr.execute(
        """
        SELECT id, arch_db
        FROM ir_ui_view
        WHERE model = %s
          AND arch_db::text LIKE %s
        """,
        (model, arch_filter),
    )
    for view_id, arch_db in cr.fetchall():
        if isinstance(arch_db, str):
            arch_db = json.loads(arch_db)
        new_arch_db = {}
        changed = False
        for lang, arch in arch_db.items():
            new_arch = pattern.sub('', arch)
            new_arch_db[lang] = new_arch
            changed = changed or new_arch != arch
        if changed:
            cr.execute(
                "UPDATE ir_ui_view SET arch_db = %s::jsonb, write_date = NOW() AT TIME ZONE 'UTC' WHERE id = %s",
                (json.dumps(new_arch_db), view_id),
            )


def migrate(cr, version):
    """Clean legacy Odoo 17 views before module data is loaded."""
    _clean_arch_db(
        cr,
        'res.partner',
        re.compile(r'<field[^>]*name="available_peppol_eas"[^>]*/>\s*', re.MULTILINE),
        '%available_peppol_eas%',
    )
    _clean_arch_db(
        cr,
        'res.partner',
        re.compile(
            r'\s*widget="filterable_selection"\s*'
            r'options="\{\'whitelist_fname\': \'available_peppol_eas\'\}"',
            re.MULTILINE,
        ),
        '%available_peppol_eas%',
    )
    _clean_arch_db(
        cr,
        'sale.order',
        re.compile(r'<field[^>]*name="translated_product_name"[^>]*/>\s*', re.MULTILINE),
        '%translated_product_name%',
    )
    _clean_arch_db(
        cr,
        'res.partner',
        re.compile(
            r'<div[^>]*duplicate_bank_partner_ids[^>]*>.*?</div>\s*',
            re.MULTILINE | re.DOTALL,
        ),
        '%duplicate_bank_partner_ids%',
    )
    _clean_arch_db(
        cr,
        'res.partner',
        re.compile(r'<field[^>]*name="duplicate_bank_partner_ids"[^>]*/>\s*', re.MULTILINE),
        '%duplicate_bank_partner_ids%',
    )
