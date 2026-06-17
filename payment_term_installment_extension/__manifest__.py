# -*- coding: utf-8 -*-
{
    "name": "Payment Term Installment Extension",
    "version": "18.0.1.0.0",
    'sequence': 10,

    "category": "Accounting",
    "summary": "Add installment fields to payment terms",
    "description": """
        Payment Term Installment Extension
        ==================================
        
        This module extends payment terms with installment-related fields:
        
        * is_installment_term - Indicates if this payment term is for installments
        * installment_count - Number of installments
        * first_payment_percentage - Percentage of first payment
    """,
    "author": "Your Company",
    "website": "https://www.yourcompany.com",
    "depends": ["account", "product"],
    "data": [
        "security/installment_settings_groups.xml",
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/account_payment_term_views.xml",
        "views/account_move_views.xml",
    ],
    "license": "LGPL-3",
    "application": True,
    "installable": True,
    "auto_install": False,
}

