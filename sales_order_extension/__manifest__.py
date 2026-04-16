{
    "name": "Sale Order Extension",
    "version": "18.0.1.0.3",
    "summary": "",
    "description": """
      
    """,
    "author": "Your Company",
    "depends": ['sale_management','product'],
    "data": [
        # "security/ir.model.access.csv",
        # "data/ir_sequence.xml",
        # "views/account_move_views.xml",
        "views/sales_orders_view.xml",
        "views/product_template_views.xml",
        "views/sale_order_type_views.xml",
        "views/product_attribute_views.xml",
        "views/menu_view.xml",
    ],
    # "i18n": [
    #     "i18n/ar.po",
    #     "i18n/account_invoice_installments.pot",
    # ],
    "license": "LGPL-3",
    "application": False,
    "installable": True,
    "auto_install": False,

}
