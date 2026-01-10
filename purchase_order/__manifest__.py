# pylint: skip-file
{
    "name": "Purchase Order Status",
    "summary": "",
    "author": "",
    "website": "",
    "version": "1.0.0",
    "category": "",
    "license": "AGPL-3",
    "depends": [
        "sale",
        "purchase"
    ],
    "data": [
        "views/purchase_order_view.xml",
    ],
'assets': {
        'web.assets_backend': [
            # 'partner_autocomplete/static/src/xml/partner_autocomplete.xml',  # مهم جدًا
            'product_matrix/static/src/js/product_matrix_dialog.js',
            'purchase_order/static/src/js/dialog/product_list.js',
            'purchase_order/static/src/js/dialog/purchase_product_configurator_dialog.js',
            'purchase_order/static/src/xml/grid.xml',

            # 'sale/static/src/js/product_configurator_dialog/product_configurator_dialog.xml',
            # # 'sale/static/src/js/product_configurator_dialog/product_configurator_dialog.js',
            # # 'purchase_order/static/src/js/dialog/product_list.js',
            # 'purchase_order/static/src/js/dialog/purchase_product_configurator_dialog.js',

        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}
