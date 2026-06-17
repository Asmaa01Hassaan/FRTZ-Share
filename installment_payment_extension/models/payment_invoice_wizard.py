# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PaymentInvoiceWizard(models.TransientModel):
    _name = 'payment.invoice.wizard'
    _description = 'Payment Invoice Wizard'

    payment_id = fields.Many2one(
        'account.payment',
        string='Payment',
        required=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        related='payment_id.partner_id',
        readonly=True,
    )
    invoice_ids = fields.One2many(
        'payment.invoice.wizard.line',
        'wizard_id',
        string='Invoices',
        required=True,
    )
    total_due_amount = fields.Monetary(
        string='Total Due Amount',
        currency_field='currency_id',
        compute='_compute_totals',
        help='Sum of all due amounts',
    )
    total_to_pay = fields.Monetary(
        string='Total To Pay',
        currency_field='currency_id',
        compute='_compute_totals',
        help='Sum of all to_pay amounts',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='payment_id.currency_id',
        readonly=True,
    )

    @api.depends('invoice_ids.due_amount', 'invoice_ids.to_pay')
    def _compute_totals(self):
        for wizard in self:
            wizard.total_due_amount = sum(wizard.invoice_ids.mapped('due_amount'))
            wizard.total_to_pay = sum(wizard.invoice_ids.mapped('to_pay'))

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'payment_id' in fields_list and self.env.context.get('default_payment_id'):
            payment_id = self.env.context.get('default_payment_id')
            payment = self.env['account.payment'].browse(payment_id)

            if payment.partner_id:
                invoices = self.env['account.move'].search([
                    ('partner_id', 'child_of', payment.partner_id.id),
                    ('move_type', '=', 'out_invoice'),
                    ('state', '=', 'posted'),
                    ('payment_state', '!=', 'paid'),
                ])
                line_vals = []
                for invoice in invoices:
                    line_vals.append((0, 0, {
                        'invoice_id': invoice.id,
                        'due_date_filter': getattr(invoice, 'due_date_filter', False),
                        'to_pay': 0.0,
                    }))
                res['invoice_ids'] = line_vals
                res['payment_id'] = payment_id
        return res

    def action_pay_all_invoices(self):
        self.ensure_one()
        if not self.invoice_ids:
            raise UserError(_("No invoices to process"))

        processed_count = 0
        for line in self.invoice_ids.filtered(lambda l: l.to_pay > 0):
            if not line.due_date_filter:
                raise UserError(_("Please select Date for Pay for invoice %s") % line.invoice_id.name)

            line.invoice_id.write({
                'to_pay_amount': line.to_pay,
                'due_date_filter': line.due_date_filter,
            })
            try:
                line.invoice_id.action_pay_installments()
                processed_count += 1
            except Exception as e:
                raise UserError(_("Error processing invoice %s: %s") % (line.invoice_id.name, str(e)))

        if processed_count > 0:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Payment processed for %d invoice(s) successfully.') % processed_count,
                    'type': 'success',
                    'sticky': False,
                },
            }
        raise UserError(_("No payments to process. Please set to_pay > 0 for at least one invoice."))


class PaymentInvoiceWizardLine(models.TransientModel):
    _name = 'payment.invoice.wizard.line'
    _description = 'Payment Invoice Wizard Line'
    _rec_name = 'invoice_id'

    wizard_id = fields.Many2one(
        'payment.invoice.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        required=True,
        readonly=True,
    )
    invoice_name = fields.Char(
        string='Transaction',
        related='invoice_id.name',
        readonly=True,
    )
    invoice_date = fields.Date(
        string='Transaction Date',
        related='invoice_id.invoice_date',
        readonly=True,
    )
    amount_total = fields.Monetary(
        string='Total Amount',
        currency_field='currency_id',
        related='invoice_id.amount_total',
        readonly=True,
    )
    total_remaining_amount = fields.Monetary(
        string='Remaining Amount',
        currency_field='currency_id',
        related='invoice_id.total_remaining_amount',
        readonly=True,
    )
    due_date_filter = fields.Date(
        string='Date for Pay',
        help='Date filter for calculating due amount',
    )
    due_amount = fields.Monetary(
        string='Due Amount',
        currency_field='currency_id',
        compute='_compute_due_amount',
        readonly=True,
        help='Due amount based on date filter',
    )
    to_pay = fields.Monetary(
        string='To Pay',
        currency_field='currency_id',
        default=0.0,
        help='Amount to pay for this invoice',
    )
    amount_to_pay = fields.Monetary(
        string='Amount to Pay',
        currency_field='currency_id',
        compute='_compute_amount_to_pay',
        readonly=True,
        help='Same as to_pay',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='invoice_id.currency_id',
        readonly=True,
    )

    @api.depends('to_pay')
    def _compute_amount_to_pay(self):
        for line in self:
            line.amount_to_pay = line.to_pay or 0.0

    @api.depends('invoice_id', 'due_date_filter', 'invoice_id.due_amount')
    def _compute_due_amount(self):
        for line in self:
            if line.invoice_id and line.due_date_filter:
                if getattr(line.invoice_id, 'due_date_filter', None) != line.due_date_filter:
                    line.invoice_id.due_date_filter = line.due_date_filter
                    if hasattr(line.invoice_id, '_compute_due_amount'):
                        line.invoice_id._compute_due_amount()
                line.due_amount = getattr(line.invoice_id, 'due_amount', 0.0)
            else:
                line.due_amount = 0.0

    @api.onchange('due_date_filter')
    def _onchange_due_date_filter(self):
        if self.invoice_id and self.due_date_filter and hasattr(self.invoice_id, 'due_date_filter'):
            self.invoice_id.due_date_filter = self.due_date_filter
            if hasattr(self.invoice_id, '_compute_due_amount'):
                self.invoice_id._compute_due_amount()
            self._compute_due_amount()
