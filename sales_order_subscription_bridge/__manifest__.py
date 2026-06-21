{
    "name": "Sales Order Subscription Bridge",
    "version": "18.0.1.0.1",
    "summary": "Limit subscription features to subscription sale order types",
    "depends": [
        "sales_order_extension",
        "sttl_sale_subscription",
    ],
    "data": [
        "views/sale_order_views.xml",
        "views/subscription_menu_views.xml",
        "views/subscription_menus.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "auto_install": True,
    "application": False,
}
