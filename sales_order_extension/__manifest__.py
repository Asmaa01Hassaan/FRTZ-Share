{
    "name": "Sale Order Extension",
    "version": "18.0.1.0.8",
    "post_init_hook": "post_init_hook",
    "summary": "",
    "description": """
      
    """,
    "author": "Your Company",
    "depends": ['sale_management', 'account', 'product', 'payment_term_installment_extension'],
    "data": [
        "security/ir.model.access.csv",
        "views/sales_orders_view.xml",
        "views/product_template_views.xml",
        "views/sale_order_type_views.xml",
        "views/product_attribute_views.xml",
        "views/menu_view.xml",
    ],
    "i18n": [
        "i18n/ar.po",
        "i18n/ar_001.po",
    ],
    "license": "LGPL-3",
    "application": False,
    "installable": True,
    "auto_install": False,

}
