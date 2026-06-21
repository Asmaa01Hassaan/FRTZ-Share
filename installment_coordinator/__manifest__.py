# -*- coding: utf-8 -*-
{
    'name': 'Installment Coordinator',
    'version': '18.0.1.0.0',
    'sequence': 25,
    'summary': 'High-level orchestration of installment operations',
    'description': """
        Installment Coordinator
        ======================

        Coordinates installment operations across modules at a high level.

        Existing modules unchanged. New code uses coordinator for clean,
        decoupled access to installment functionality.

        Features:
        - High-level operation orchestration
        - Automatic installment creation on invoice posting
        - Automatic payment tracking
        - Automatic overdue detection
        - Dashboard and monitoring
        - Dependency validation

        Example:
            coordinator = self.env['installment.coordinator']
            coordinator.on_invoice_posted(invoice)
            coordinator.on_payment_received(payment)
    """,
    'author': 'FRTZ Team',
    'website': 'https://frtz.com',
    'depends': [
        'installment_dependency_manager',
        'installment_adapter',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/installment_coordinator_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
