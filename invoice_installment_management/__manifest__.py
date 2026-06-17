# -*- coding: utf-8 -*-
{
    "name": "Invoice Installment Management",
    "version": "18.0.1.0.0",
    'sequence': 10,

    "category": "Accounting",
    "summary": "Manage invoice installments based on payment terms",
    "description": """
        Invoice Installment Management
        =============================
        
        This module manages invoice installments based on payment terms:
        
        * Creates installments from payment term line_ids when is_installment_term = True
        * Displays installments in invoice view
        * Tracks installment payments and status
    """,
    "author": "Your Company",
    "website": "https://www.yourcompany.com",
    "depends": ["account", "sale", "payment_term_installment_extension"],
    "data": [
        "data/ir_sequence_data.xml",
        "security/ir.model.access.csv",
        "views/account_move_installment_views.xml",
        "views/account_move_views.xml",
        "views/account_payment_register_views.xml",
    ],
    "license": "LGPL-3",
    "application": False,
    "installable": True,
    "auto_install": False,
    "post_init_hook": "post_init_hook",
}

