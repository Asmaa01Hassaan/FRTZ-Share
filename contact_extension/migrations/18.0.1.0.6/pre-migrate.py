import json
import re

ENTERPRISE_MODULES = (
    'account_accountant',
    'account_accountant_check_printing',
    'account_asset',
    'account_auto_transfer',
    'account_bank_statement_extract',
    'account_bank_statement_import',
    'account_bank_statement_import_camt',
    'account_bank_statement_import_csv',
    'account_bank_statement_import_ofx',
    'account_base_import',
    'account_disallowed_expenses',
    'account_extract',
    'account_followup',
    'account_invoice_extract',
    'account_invoice_extract_purchase',
    'account_loans',
    'account_online_synchronization',
    'account_reports',
    'account_reports_cash_basis',
    'accountant',
    'analytic_enterprise',
    'contacts_enterprise',
    'currency_rate_live',
    'database_expiration_remover',
    'digest_enterprise',
    'iap_extract',
    'mail_enterprise',
    'mail_mobile',
    'product_barcodelookup',
    'sale_account_accountant',
    'spreadsheet_dashboard_account_accountant',
    'spreadsheet_dashboard_edition',
    'spreadsheet_dashboard_purchase_stock',
    'spreadsheet_dashboard_stock',
    'spreadsheet_edition',
    'spreadsheet_sale_management',
    'stock_accountant',
    'stock_barcode',
    'stock_enterprise',
    'web_cohort',
    'web_enterprise',
    'web_gantt',
    'web_grid',
    'web_map',
    'web_mobile',
)


def _clean_arch_db(cr, model, patterns, arch_filter):
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
            new_arch = arch
            for pattern in patterns:
                new_arch = pattern.sub('', new_arch)
            new_arch_db[lang] = new_arch
            changed = changed or new_arch != arch
        if changed:
            cr.execute(
                "UPDATE ir_ui_view SET arch_db = %s::jsonb, write_date = NOW() AT TIME ZONE 'UTC' WHERE id = %s",
                (json.dumps(new_arch_db), view_id),
            )


def _delete_enterprise_views(cr):
    cr.execute(
        """
        SELECT res_id
        FROM ir_model_data
        WHERE module = ANY(%s)
          AND model = 'ir.ui.view'
          AND res_id IS NOT NULL
        """,
        (list(ENTERPRISE_MODULES),),
    )
    view_ids = [row[0] for row in cr.fetchall()]
    if view_ids:
        cr.execute("DELETE FROM ir_ui_view WHERE id = ANY(%s)", (view_ids,))


def migrate(cr, version):
    """Remove orphaned enterprise sale spreadsheet views and field references."""
    _delete_enterprise_views(cr)

    spreadsheet_patterns = [
        re.compile(
            r'<button[^>]*action_open_sale_order_spreadsheet[^>]*>.*?</button>\s*',
            re.MULTILINE | re.DOTALL,
        ),
        re.compile(r'<field[^>]*name="spreadsheet_template_id"[^>]*/>\s*', re.MULTILINE),
        re.compile(r'<field[^>]*name="spreadsheet_id"[^>]*/>\s*', re.MULTILINE),
    ]
    for model, arch_filter in (
        ('sale.order', '%spreadsheet_template_id%'),
        ('sale.order', '%spreadsheet_id%'),
        ('sale.order.template', '%spreadsheet_template_id%'),
        ('sale.order.template', '%spreadsheet_id%'),
    ):
        _clean_arch_db(cr, model, spreadsheet_patterns, arch_filter)
