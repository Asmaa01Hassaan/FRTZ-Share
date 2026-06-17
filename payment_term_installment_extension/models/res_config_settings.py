# -*- coding: utf-8 -*-
from odoo import fields, models

INSTALLMENT_FIELD_DISPLAY = [
    ('visible', 'Editable'),
    ('readonly', 'Read Only'),
    ('invisible', 'Invisible'),
]


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    installment_default_scope = fields.Selection(
        [
            ('per_invoice', 'Per Invoice'),
            ('per_lines', 'Per Lines'),
        ],
        string='Default Scope',
        config_parameter='payment_term_installment_extension.default_scope',
        default='per_lines',
        help='Default scope applied on new sales orders, invoices, and payment terms.',
    )
    installment_scope_display = fields.Selection(
        INSTALLMENT_FIELD_DISPLAY,
        string='Scope on Forms',
        config_parameter='payment_term_installment_extension.scope_display',
        default='visible',
        help='How the Scope field appears on sales orders, invoices, and payment terms.',
    )
    installment_default_baseline_date = fields.Selection(
        [
            ('invoice_date', 'Invoice Date'),
            ('posting_date', 'Posting Date'),
            ('receipt_date', 'Receipt Date'),
        ],
        string='Default Baseline Date',
        config_parameter='payment_term_installment_extension.default_baseline_date',
        default='invoice_date',
        help='Default baseline date applied on new sales orders, invoices, and payment terms.',
    )
    installment_baseline_date_display = fields.Selection(
        INSTALLMENT_FIELD_DISPLAY,
        string='Baseline Date on Forms',
        config_parameter='payment_term_installment_extension.baseline_date_display',
        default='visible',
        help='How the Baseline Date field appears on sales orders, invoices, and payment terms.',
    )
