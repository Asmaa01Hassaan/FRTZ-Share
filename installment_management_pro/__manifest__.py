# -*- coding: utf-8 -*-
{
    'name': 'Installment Management Pro',
    'summary': 'Enhanced installment tracking, payment logs, rescheduling, and overdue dashboard',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'author': 'FRTZ',
    'depends': [
        'invoice_installment_management',
        'installment_payment_extension',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'views/installment_payment_log_views.xml',
        'views/installment_reschedule_log_views.xml',
        'views/installment_reschedule_wizard_views.xml',
        'views/installment_schedule_wizard_views.xml',
        'views/overdue_installments_views.xml',
        'views/account_move_installment_views.xml',
        'views/account_move_views.xml',
        'views/menu_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
