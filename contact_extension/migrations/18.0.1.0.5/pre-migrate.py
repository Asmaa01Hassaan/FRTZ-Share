ENTERPRISE_VIEW_TYPES = ('cohort', 'gantt', 'grid', 'map')

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


def migrate(cr, version):
    """Clean enterprise leftovers when running Odoo Community without enterprise addons."""
    cr.execute(
        """
        DELETE FROM ir_act_window_view
        WHERE view_id IN (
            SELECT id FROM ir_ui_view WHERE type = ANY(%s)
        )
        """,
        (list(ENTERPRISE_VIEW_TYPES),),
    )

    cr.execute(
        """
        SELECT id, view_mode
        FROM ir_act_window
        WHERE view_mode ~ '(^|,)\\s*(cohort|gantt|grid|map)\\s*(,|$)'
        """
    )
    for act_id, view_mode in cr.fetchall():
        modes = [mode for mode in view_mode.split(',') if mode not in ENTERPRISE_VIEW_TYPES]
        cr.execute(
            "UPDATE ir_act_window SET view_mode = %s WHERE id = %s",
            (','.join(modes) if modes else 'list,form', act_id),
        )

    cr.execute("DELETE FROM ir_ui_view WHERE type = ANY(%s)", (list(ENTERPRISE_VIEW_TYPES),))

    cr.execute(
        """
        DELETE FROM ir_model_fields_selection
        WHERE field_id = (
            SELECT id FROM ir_model_fields
            WHERE model = 'ir.ui.view' AND name = 'type'
        )
        AND value = ANY(%s)
        """,
        (list(ENTERPRISE_VIEW_TYPES),),
    )

    cr.execute(
        """
        UPDATE ir_module_module
        SET state = 'uninstalled'
        WHERE name = ANY(%s)
          AND state = 'installed'
        """,
        (list(ENTERPRISE_MODULES),),
    )
