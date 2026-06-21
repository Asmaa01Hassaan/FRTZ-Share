# -*- coding: utf-8 -*-
{
    'name': 'Installment Adapter',
    'version': '18.0.1.0.0',
    'sequence': 20,
    'summary': 'Adapter layer that wraps existing installment functionality',
    'description': """
        Installment Adapter
        ===================

        Provides a clean, unified interface to existing installment modules
        without modifying their code.

        Acts as a facade/adapter pattern - existing modules unchanged,
        new code uses the adapter for cleaner, decoupled access.

        Features:
        - Facade over existing installment operations
        - Clean service API
        - Dependency-aware operations
        - Error handling and logging

        IMPORTANT: This module wraps existing functionality without changing it.
    """,
    'author': 'FRTZ Team',
    'website': 'https://frtz.com',
    'depends': [
        'installment_dependency_manager',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/installment_adapter_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
