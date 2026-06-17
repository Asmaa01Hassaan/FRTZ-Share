# -*- coding: utf-8 -*-
{
    "name": "Pricelist Expression",
    "summary": "Expression-based pricing with installment support",
    "description": """
        This module adds expression-based pricing to pricelist rules with:
        - Python expression evaluation for dynamic pricing
        - Installment-aware pricing calculations
        - Context variables: price, cost, qty, installment_num, first_payment
        - Safe expression evaluation with error handling
        - Real-time price updates on installment changes
    """,
    "version": "18.0.1.0.0",
    "category": "Sales/Price Lists",
    "author": "Your Company",
    "depends": ["product", "sale", "account", "account_invoice_installments"],
    "data": [
        "views/pricelist_item_views.xml",
        "views/account_move_views.xml",
        "views/res_config_settings_views.xml",
        "security/ir.model.access.csv"
    ],
    "i18n": [
        "i18n/ar.po",
        "i18n/pricelist_expression.pot",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "auto_install": False,
}