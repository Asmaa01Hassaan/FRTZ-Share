# -*- coding: utf-8 -*-
{
    'name': 'Installment Payment Extension',
    'summary': 'Pay installments from payment form: control payments and Pay for Invoices wizard',
    'description': """
        Installment Payment Extension
        ==============================
        Extends the payment flow to support installment payment:

        * From Invoice: Date for Pay + Amount to pay + "Pay Installment" (action_pay_installments).
        * From Payment:
          - Control payments: load unpaid invoices, set to_pay and due_date per invoice;
            on confirm (action_post) process control payments and link account.installment.payment.log.
          - Pay for Invoices wizard: set Date for Pay and amount to pay per invoice, then process all.

        Depends on invoice_installment_management for installments and action_pay_installments.
    """,
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'account',
        'invoice_installment_management',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/payment_invoice_wizard_views.xml',
        'views/control_payment_views.xml',
        'views/account_payment_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
