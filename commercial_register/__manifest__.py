{
    'name': 'Commercial Register',
    'version': '1.0.0',
    'category': 'Custom',
    'author': 'Your Company',
    'depends': ['base',
                'account'
             ],

    'data': [
            'views/commercial_regester_view.xml',
            'views/account_report_view.xml'
    ],

    'installable': True,
    'application': False,
    # 'post_init_hook': 'post_init_create_fields',
}
