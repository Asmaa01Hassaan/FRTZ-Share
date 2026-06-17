# -*- coding: utf-8 -*-
{
    'name': 'Database Expiration Remover',
    'version': '18.0.1.0.0',
    'summary': 'Prevents database from expiring by automatically extending trial period',
    'description': """
        Database Expiration Remover
        =========================
        
        This module prevents the database from expiring by:
        - Automatically extending the trial period
        - Resetting expiration dates
        - Bypassing expiration checks
        - Maintaining database functionality
        
        Features:
        - Automatic trial extension
        - Expiration date reset
        - Database maintenance
        - Trial period management
    """,
    'category': 'Tools',
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'web_enterprise'],
    'data': [
        'security/ir.model.access.csv',
        'data/database_expiration_data.xml',
        'views/database_expiration_views.xml',
        'views/database_expiration_core_views.xml',
        'views/webclient_override.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'database_expiration_remover/static/src/css/database_expiration.css',
            'database_expiration_remover/static/src/css/expiration_override.css',
        ],
        'web.assets_web': [
            'database_expiration_remover/static/src/js/database_expiration.js',
            'database_expiration_remover/static/src/js/expiration_override.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': True,
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
}
