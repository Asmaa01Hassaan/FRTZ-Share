"""Remove stale enterprise model metadata that triggers Missing model log noise."""

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

_ENTERPRISE_ONLY_MODELS_SQL = """
    SELECT m.id, m.model
    FROM ir_model m
    WHERE EXISTS (
        SELECT 1
        FROM ir_model_data d
        WHERE d.model = 'ir.model' AND d.res_id = m.id
          AND d.module = ANY(%(modules)s)
    )
    AND NOT EXISTS (
        SELECT 1
        FROM ir_model_data d
        WHERE d.model = 'ir.model' AND d.res_id = m.id
          AND d.module != ALL(%(modules)s)
    )
"""


def _delete_enterprise_menus(cr, modules):
    """Delete enterprise menus leaf-first to satisfy parent_id FK constraints."""
    while True:
        cr.execute(
            """
            DELETE FROM ir_ui_menu
            WHERE id IN (
                SELECT d.res_id
                FROM ir_model_data d
                WHERE d.module = ANY(%s)
                  AND d.model = 'ir.ui.menu'
                  AND d.res_id IS NOT NULL
            )
            AND NOT EXISTS (
                SELECT 1 FROM ir_ui_menu child WHERE child.parent_id = ir_ui_menu.id
            )
            """,
            (modules,),
        )
        if cr.rowcount == 0:
            break


def _delete_enterprise_module_data(cr):
    modules = list(ENTERPRISE_MODULES)

    _delete_enterprise_menus(cr, modules)

    cr.execute(
        """
        DELETE FROM ir_cron
        WHERE id IN (
            SELECT res_id
            FROM ir_model_data
            WHERE module = ANY(%s) AND model = 'ir.cron' AND res_id IS NOT NULL
        )
        OR ir_actions_server_id IN (
            SELECT res_id
            FROM ir_model_data
            WHERE module = ANY(%s) AND model = 'ir.actions.server' AND res_id IS NOT NULL
        )
        """,
        (modules, modules),
    )

    cr.execute(
        """
        DELETE FROM ir_act_window
        WHERE id IN (
            SELECT res_id
            FROM ir_model_data
            WHERE module = ANY(%s) AND model = 'ir.actions.act_window' AND res_id IS NOT NULL
        )
        """,
        (modules,),
    )

    cr.execute(
        """
        DELETE FROM ir_act_server
        WHERE id IN (
            SELECT res_id
            FROM ir_model_data
            WHERE module = ANY(%s) AND model = 'ir.actions.server' AND res_id IS NOT NULL
        )
        """,
        (modules,),
    )

    while True:
        cr.execute(
            """
            DELETE FROM ir_ui_view
            WHERE id IN (
                SELECT res_id
                FROM ir_model_data
                WHERE module = ANY(%s) AND model = 'ir.ui.view' AND res_id IS NOT NULL
            )
            AND NOT EXISTS (
                SELECT 1 FROM ir_ui_view child WHERE child.inherit_id = ir_ui_view.id
            )
            """,
            (modules,),
        )
        if cr.rowcount == 0:
            break

    cr.execute(
        "DELETE FROM ir_model_data WHERE module = ANY(%s)",
        (modules,),
    )

    cr.execute(
        """
        UPDATE ir_module_module
        SET state = 'uninstalled'
        WHERE name = ANY(%s) AND state = 'installed'
        """,
        (modules,),
    )


def _delete_enterprise_only_model_metadata(cr):
    """Drop access rules and actions for models owned exclusively by enterprise."""
    cr.execute(
        _ENTERPRISE_ONLY_MODELS_SQL,
        {'modules': list(ENTERPRISE_MODULES)},
    )
    enterprise_models = cr.fetchall()
    if not enterprise_models:
        return

    model_ids = [row[0] for row in enterprise_models]
    model_names = [row[1] for row in enterprise_models]

    cr.execute("DELETE FROM ir_model_access WHERE model_id = ANY(%s)", (model_ids,))
    cr.execute("DELETE FROM ir_rule WHERE model_id = ANY(%s)", (model_ids,))
    cr.execute(
        """
        DELETE FROM ir_cron
        WHERE ir_actions_server_id IN (
            SELECT id FROM ir_act_server
            WHERE model_id = ANY(%s) OR model_name = ANY(%s)
        )
        """,
        (model_ids, model_names),
    )
    cr.execute(
        "DELETE FROM ir_act_window WHERE res_model = ANY(%s)",
        (model_names,),
    )
    cr.execute(
        "DELETE FROM ir_act_report_xml WHERE model = ANY(%s)",
        (model_names,),
    )
    cr.execute(
        """
        DELETE FROM ir_act_server
        WHERE model_id = ANY(%s) OR model_name = ANY(%s)
        """,
        (model_ids, model_names),
    )
    cr.execute(
        """
        DELETE FROM ir_act_client
        WHERE binding_model_id = ANY(%s)
        """,
        (model_ids,),
    )
    cr.execute(
        "DELETE FROM ir_model_fields WHERE model_id = ANY(%s)",
        (model_ids,),
    )
    cr.execute("DELETE FROM ir_model WHERE id = ANY(%s)", (model_ids,))


def migrate(cr, version):
    _delete_enterprise_module_data(cr)
    _delete_enterprise_only_model_metadata(cr)
