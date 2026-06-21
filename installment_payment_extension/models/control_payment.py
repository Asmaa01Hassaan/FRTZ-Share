# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ControlPayment(models.Model):
    _name = 'control.payment'
    _description = 'Control Payment'
    _rec_name = 'display_name'
    _order = 'invoice_date desc, id desc'

    payment_id = fields.Many2one(
        'account.payment',
        string='Payment',
        required=True,
        ondelete='cascade',
        index=True,
    )
    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        ondelete='cascade',
        index=True,
    )
    installment_id = fields.Many2one(
        'account.move.installment',
        string='Installment',
        ondelete='cascade',
        index=True,
    )
    invoice_line_id = fields.Many2one(
        'account.move.line',
        string='Invoice Line',
        ondelete='cascade',
        index=True,
    )

    installment_reference = fields.Char(
        string='Reference',
        compute='_compute_installment_reference',
        store=True,
    )

    @api.depends('installment_id', 'installment_id.name', 'installment_id.move_id.name',
                 'invoice_line_id', 'invoice_line_id.product_id.display_name',
                 'invoice_id', 'invoice_id.name')
    def _compute_installment_reference(self):
        for record in self:
            if record.installment_id:
                if hasattr(record.installment_id, 'display_reference') and record.installment_id.display_reference:
                    record.installment_reference = record.installment_id.display_reference
                else:
                    move_name = record.installment_id.move_id.name or ''
                    record.installment_reference = f"{move_name} - {record.installment_id.name}"
            elif record.invoice_line_id and record.invoice_id:
                inv_name = record.invoice_id.name or ''
                product_name = record.invoice_line_id.product_id.display_name or record.invoice_line_id.name or ''
                record.installment_reference = f"{inv_name} - {product_name}"
            elif record.invoice_id:
                record.installment_reference = record.invoice_id.name or ''
            else:
                record.installment_reference = ''

    invoice_name = fields.Char(
        string='Transaction',
        related='invoice_id.name',
        readonly=True,
        store=True,
    )
    invoice_date = fields.Date(
        string='Transaction Date',
        compute='_compute_line_amounts',
        store=True,
    )
    amount_total = fields.Monetary(
        string='Total Amount',
        currency_field='currency_id',
        compute='_compute_line_amounts',
        store=True,
    )
    total_remaining_amount = fields.Monetary(
        string='Remaining Amount',
        currency_field='currency_id',
        compute='_compute_line_amounts',
        store=True,
    )

    @api.depends(
        'installment_id', 'installment_id.amount_total', 'installment_id.amount_residual',
        'installment_id.date_invoice',
        'invoice_line_id',
        'invoice_id', 'invoice_id.amount_total', 'invoice_id.total_remaining_amount',
        'invoice_id.invoice_date', 'invoice_id.installment_ids.amount_total',
        'invoice_id.installment_ids.amount_residual', 'invoice_id.installment_ids.invoice_line_id',
    )
    def _compute_line_amounts(self):
        for record in self:
            if record.installment_id:
                record.invoice_date = record.installment_id.date_invoice
                record.amount_total = record.installment_id.amount_total
                record.total_remaining_amount = record.installment_id.amount_residual
            elif record.invoice_line_id and record.invoice_id:
                # by_product_invoice: sum installments for this invoice line
                record.invoice_date = record.invoice_id.invoice_date
                line_installments = record.invoice_id.installment_ids.filtered(
                    lambda i: i.invoice_line_id.id == record.invoice_line_id.id
                )
                record.amount_total = sum(line_installments.mapped('amount_total'))
                record.total_remaining_amount = sum(line_installments.mapped('amount_residual'))
            elif record.invoice_id:
                record.invoice_date = record.invoice_id.invoice_date
                record.amount_total = record.invoice_id.amount_total
                record.total_remaining_amount = record.invoice_id.total_remaining_amount
            else:
                record.invoice_date = False
                record.amount_total = 0.0
                record.total_remaining_amount = 0.0

    due_amount = fields.Monetary(
        string='Due Amount',
        currency_field='currency_id',
        compute='_compute_due_amount',
        readonly=True,
        help='Due amount (computed from invoice or installment)',
    )

    @api.depends('invoice_id', 'invoice_id.due_amount', 'invoice_id.due_date_filter',
                 'installment_id', 'installment_id.amount_residual', 'installment_id.state',
                 'installment_id.date_due', 'invoice_line_id', 'due_date',
                 'invoice_id.installment_ids.amount_residual',
                 'invoice_id.installment_ids.date_due',
                 'invoice_id.installment_ids.state',
                 'invoice_id.installment_ids.invoice_line_id')
    def _compute_due_amount(self):
        for record in self:
            if record.installment_id:
                inst = record.installment_id
                if inst.amount_residual > 0 and inst.state in ('draft', 'due', 'partial', 'overdue'):
                    if record.due_date and inst.date_due:
                        record.due_amount = inst.amount_residual if inst.date_due <= record.due_date else 0.0
                    else:
                        record.due_amount = inst.amount_residual
                else:
                    record.due_amount = 0.0
                continue

            if record.invoice_line_id and record.invoice_id:
                # by_product_invoice: sum due installments for this invoice line
                line_installments = record.invoice_id.installment_ids.filtered(
                    lambda i: i.invoice_line_id.id == record.invoice_line_id.id
                    and i.amount_residual > 0
                    and i.state in ('draft', 'due', 'partial', 'overdue')
                )
                if record.due_date:
                    line_installments = line_installments.filtered(
                        lambda i: i.date_due and i.date_due <= record.due_date
                    )
                record.due_amount = sum(line_installments.mapped('amount_residual'))
                continue

            if not record.invoice_id:
                record.due_amount = 0.0
                continue
            selected_product = record.payment_id.selected_product_id if record.payment_id else False
            if record.payment_id and record.payment_id.payment_scope == 'by_invoice_lines' and selected_product:
                record.invoice_id.product_filter_id = selected_product.id
            else:
                record.invoice_id.product_filter_id = False
            if record.due_date and getattr(record.invoice_id, 'due_date_filter', None) != record.due_date:
                record.invoice_id.due_date_filter = record.due_date
            if hasattr(record.invoice_id, '_compute_due_amount'):
                record.invoice_id._compute_due_amount()
            record.due_amount = getattr(record.invoice_id, 'due_amount', 0.0) or 0.0

    @api.onchange('due_date', 'invoice_id')
    def _onchange_due_date(self):
        if self.installment_id:
            self._compute_due_amount()
            return
        if self.invoice_id and self.due_date and hasattr(self.invoice_id, 'due_date_filter'):
            self.invoice_id.due_date_filter = self.due_date
            if hasattr(self.invoice_id, '_compute_due_amount'):
                self.invoice_id._compute_due_amount()
            self._compute_due_amount()

    @api.onchange('to_pay')
    def _onchange_to_pay(self):
        if self.payment_id:
            self.payment_id._compute_total_control_to_pay()

    due_date = fields.Date(
        string='Due Date',
        help='Date filter for calculating due amount on invoice',
    )
    to_pay = fields.Monetary(
        string='To Pay',
        currency_field='currency_id',
        default=0.0,
        help='Amount to pay for this invoice',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='payment_id.currency_id',
        store=True,
        readonly=True,
    )
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
    )

    @api.depends('invoice_id.name', 'installment_id.name', 'payment_id.name', 'to_pay')
    def _compute_display_name(self):
        for record in self:
            payment_name = record.payment_id.name if record.payment_id else ''
            if record.installment_id:
                ref = record.installment_reference or record.installment_id.name
                record.display_name = f"{payment_name} - {ref} - {record.to_pay}"
            elif record.invoice_id:
                record.display_name = f"{payment_name} - {record.invoice_id.name} - {record.to_pay}"
            else:
                record.display_name = _('New')

    @api.model
    def create(self, vals_list):
        if not isinstance(vals_list, list):
            vals_list = [vals_list]
        for vals in vals_list:
            if vals.get('installment_id') and not vals.get('invoice_id'):
                inst = self.env['account.move.installment'].browse(vals['installment_id'])
                if inst.exists():
                    vals['invoice_id'] = inst.move_id.id
            if vals.get('invoice_line_id') and not vals.get('invoice_id'):
                line = self.env['account.move.line'].browse(vals['invoice_line_id'])
                if line.exists():
                    vals['invoice_id'] = line.move_id.id
            if vals.get('due_date') and vals.get('invoice_id') and not vals.get('installment_id'):
                invoice = self.env['account.move'].browse(vals['invoice_id'])
                if getattr(invoice, 'due_date_filter', None) != vals['due_date']:
                    invoice.due_date_filter = vals['due_date']
                    if hasattr(invoice, '_compute_due_amount'):
                        invoice._compute_due_amount()
        records = super().create(vals_list)
        for record in records:
            record._compute_due_amount()
        return records

    def write(self, vals):
        result = super().write(vals)
        if 'to_pay' in vals:
            for record in self:
                if record.payment_id:
                    record.payment_id._compute_total_control_to_pay()
        return result
