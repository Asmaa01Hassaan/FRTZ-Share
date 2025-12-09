# -*- coding: utf-8 -*-
{
    'name': 'Vertical Menu Theme',
    'version': '18.0.1.0.0',
    'summary': 'Custom theme to make Odoo menu sections vertical',
    'description': """
        Vertical Menu Theme
        ==================
        
        This module provides a custom theme that makes the Odoo menu sections vertical instead of horizontal.
        
        Features:
        - Vertical menu layout
        - Improved navigation experience
        - Responsive design
        - Custom styling for menu items
    """,
    'category': 'Theme/Backend',
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'web','sale'],
    'data': [
        'views/navbar_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # 'vertical_menu_theme/static/src/css/vertical_menu.css',
            '/vertical_menu_theme/static/src/js/vertical_menu.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
