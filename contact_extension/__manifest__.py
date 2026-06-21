{
    "name": "Contact Extension",
    'sequence': 2,
    "version": "18.0.1.0.9",
    "summary": "",
    "license": "LGPL-3",
    "author": "Asmaa Hassaan",
    "depends": ['base', 'contacts', 'account', 'sale'],
    "data": [
        "security/ir.model.access.csv",
        "views/contact_addresses_views.xml",
        "views/contact_base_info_views.xml",
        "views/customer_guarantees_view.xml",
        "views/sale_order_views.xml",
        "views/account_move_views.xml",
    ],

    'installable': True,
    'auto_install': False,
    'application': True,
}
