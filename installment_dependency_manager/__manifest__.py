# -*- coding: utf-8 -*-
{
    'name': 'Installment Dependency Manager',
    'version': '18.0.1.0.0',
    'sequence': 5,
    'summary': 'Provides abstract interface for installment operations',
    'description': """
        Installment Dependency Manager
        ==============================

        This module provides a registry system to track installment module dependencies
        and capabilities without modifying existing modules.

        Features:
        - Detects installed installment modules
        - Provides capability registry
        - Tracks module dependencies
        - Defines abstract interfaces

        IMPORTANT: This module does NOT change any existing module logic.
        It provides an optional dependency management layer.
    """,
    'author': 'FRTZ Team',
    'website': 'https://frtz.com',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/dependency_registry_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
