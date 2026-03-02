{
    'name': 'Report Inventory',
    'version': '1.0.0',
    'category': 'Custom',
    'author': 'Your Company',

    'depends': ['base'],

    'data': [
        'report/x_inventory_report.xml',
    ],

    'installable': True,
    'application': False,
    # 'post_init_hook': 'post_init_create_fields',
}
