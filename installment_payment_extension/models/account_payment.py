# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare
import logging

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        domain="[('type', '!=', 'private')]",
    )
    person = fields.Boolean(default=True, string="Person")
    is_dividend_eligible = fields.Boolean(
        string=_('Dividend Eligible'),
        default=False,
        help=_('Mark this payment as eligible for dividend processing.'),
    )

    def action_post(self):
        """Override action_post to process control payments before posting"""
        draft_payments = self.filtered(lambda payment: payment.state == 'draft')
        if draft_payments:
            draft_payments._auto_fill_control_payment_from_memo()
        if self.control_payment_ids and any(self.control_payment_ids.mapped('to_pay')):
            try:
                self.with_context(from_action_post=True).action_process_control_payments()
            except Exception as e:
                _logger.warning(
                    "Error processing control payments for payment %s: %s",
                    self.name,
                    e,
                )
        return super().action_post()

    payment_due_date_filter = fields.Date(
        string=_('Date for Pay'),
        help=_('Date filter for calculating due amount on all selected invoices'),
    )

    control_payment_ids = fields.One2many(
        'control.payment',
        'payment_id',
        string=_('Control Payments'),
        help=_('Control payment records for invoices'),
    )

    total_control_to_pay = fields.Monetary(
        string=_('Total Control To Pay'),
        currency_field='currency_id',
        compute='_compute_total_control_to_pay',
        help=_('Sum of all to_pay for control payment records'),
    )

    control_payment_remaining_amount = fields.Monetary(
        string=_('Control Remaining Amount'),
        currency_field='currency_id',
        compute='_compute_total_control_to_pay',
        help=_('Payment amount minus total control to pay'),
    )

    payment_scope = fields.Selection([
        ('by_invoice', 'By Invoice'),
        ('by_invoice_lines', 'By Product'),
        ('by_all_invoice_lines', 'By Installment'),
        ('by_product_invoice', 'By Invoice Lines'),
    ], string=_('Payment Matching '), default='by_invoice',
        help=_('By Invoice: payment applies to whole invoice. By Invoice Lines: payment applies to specific products/lines.'))

    unpaid_product_ids = fields.Many2many(
        'product.product',
        'payment_unpaid_product_rel',
        'payment_id',
        'product_id',
        string=_('Available Products'),
        compute='_compute_unpaid_product_ids',
        help=_('Products from unpaid customer invoices'),
    )

    selected_product_id = fields.Many2one(
        'product.product',
        string=_('Product'),
        domain="[('id', 'in', unpaid_product_ids)]",
        help=_('Select a product to filter the transaction list to only show invoices containing this product'),
    )

    @api.depends('partner_id', 'partner_type', 'company_id')
    def _compute_unpaid_product_ids(self):
        """Compute products from unpaid customer invoices."""
        for payment in self:
            if payment.partner_type != 'customer' or not payment.partner_id:
                payment.unpaid_product_ids = [(5,)]
                continue
            commercial_partner_id = payment.partner_id.commercial_partner_id.id
            if not commercial_partner_id:
                payment.unpaid_product_ids = [(5,)]
                continue
            invoices = self.env['account.move'].search([
                ('partner_id', 'child_of', commercial_partner_id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ('not_paid', 'partial')),
                ('company_id', '=', payment.company_id.id),
            ])
            product_ids = set()
            for inv in invoices:
                for line in inv.invoice_line_ids.filtered(lambda l: l.display_type == 'product' and l.product_id):
                    product_ids.add(line.product_id.id)
            payment.unpaid_product_ids = [(6, 0, list(product_ids))]

    @api.onchange('selected_product_id', 'payment_scope')
    def _onchange_selected_product_filter(self):
        """Reload control_payment_ids based on payment_scope and selected product."""
        if not self.partner_id:
            self.control_payment_ids = [(5, 0, 0)]
            return

        if self._auto_fill_control_payment_from_memo():
            return

        due_date_value = self.payment_due_date_filter or self.date or fields.Date.today()
        commercial_id = self.partner_id.commercial_partner_id.id

        # --- By All Invoice Lines: load individual installments ---
        if self.payment_scope == 'by_all_invoice_lines':
            installments = self.env['account.move.installment'].search([
                ('partner_id', 'child_of', commercial_id),
                ('move_id.move_type', '=', 'out_invoice'),
                ('move_id.state', '=', 'posted'),
                ('amount_residual', '>', 0),
                ('state', 'in', ('draft', 'due', 'partial', 'overdue')),
            ])
            # Only include installments that are due on or before the date filter
            if due_date_value:
                installments = installments.filtered(
                    lambda i: i.date_due and i.date_due <= due_date_value
                )
            self.control_payment_ids = [(5, 0, 0)] + [(0, 0, {
                'installment_id': inst.id,
                'invoice_id': inst.move_id.id,
                'to_pay': 0.0,
                'due_date': due_date_value,
            }) for inst in installments]
            return

        # --- By Invoice Lines (product per invoice): one row per product line ---
        if self.payment_scope == 'by_product_invoice':
            invoices = self.env['account.move'].search([
                ('partner_id', 'child_of', commercial_id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', '!=', 'paid'),
                ('total_remaining_amount', '!=', 0),
                ('apply_payment_term_per_line', '=', True),
            ])
            lines_data = []
            for inv in invoices:
                seen_lines = set()
                for inst in inv.installment_ids.filtered(
                    lambda i: i.amount_residual > 0
                    and i.state in ('draft', 'due', 'partial', 'overdue')
                    and i.invoice_line_id
                ):
                    if inst.invoice_line_id.id in seen_lines:
                        continue
                    line_installments = inv.installment_ids.filtered(
                        lambda i, il=inst.invoice_line_id: i.invoice_line_id.id == il.id
                        and i.amount_residual > 0
                        and i.state in ('draft', 'due', 'partial', 'overdue')
                    )
                    if due_date_value:
                        due_installments = line_installments.filtered(
                            lambda i: i.date_due and i.date_due <= due_date_value
                        )
                    else:
                        due_installments = line_installments
                    due_total = sum(due_installments.mapped('amount_residual'))
                    if due_total > 0:
                        lines_data.append({
                            'invoice_id': inv.id,
                            'invoice_line_id': inst.invoice_line_id.id,
                            'to_pay': 0.0,
                            'due_date': due_date_value,
                        })
                    seen_lines.add(inst.invoice_line_id.id)
            self.control_payment_ids = [(5, 0, 0)] + [(0, 0, d) for d in lines_data]
            return

        # --- By Product: filter invoices by selected product ---
        if self.payment_scope == 'by_invoice_lines' and self.selected_product_id:
            invoices = self.env['account.move'].search([
                ('partner_id', 'child_of', commercial_id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', '!=', 'paid'),
                ('total_remaining_amount', '!=', 0),
                ('invoice_line_ids.product_id', '=', self.selected_product_id.id),
            ])
            for inv in invoices:
                inv.product_filter_id = self.selected_product_id.id
            self.control_payment_ids = [(5, 0, 0)] + [(0, 0, {
                'invoice_id': inv.id,
                'to_pay': 0.0,
                'due_date': due_date_value,
            }) for inv in invoices]
            return

        # --- By Invoice (default) or By Product without selection ---
        invoices = self.env['account.move'].search([
            ('partner_id', 'child_of', commercial_id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', '!=', 'paid'),
            ('total_remaining_amount', '!=', 0),
        ])
        for inv in invoices:
            inv.product_filter_id = False
            if due_date_value and hasattr(inv, 'due_date_filter'):
                inv.due_date_filter = due_date_value
                if hasattr(inv, '_compute_due_amount'):
                    inv._compute_due_amount()
        # Exclude invoices with zero due amount
        invoices = invoices.filtered(lambda inv: getattr(inv, 'due_amount', 0.0) > 0)
        self.control_payment_ids = [(5, 0, 0)] + [(0, 0, {
            'invoice_id': inv.id,
            'to_pay': 0.0,
            'due_date': due_date_value,
        }) for inv in invoices]

    @api.onchange('memo', 'amount')
    def _onchange_memo_auto_fill_transaction(self):
        self._auto_fill_control_payment_from_memo()

    def _amounts_match(self, amount1, amount2):
        self.ensure_one()
        rounding = self.currency_id.rounding if self.currency_id else 0.01
        return float_compare(amount1 or 0.0, amount2 or 0.0, precision_rounding=rounding) == 0

    def _find_invoice_from_memo(self):
        self.ensure_one()
        memo = (self.memo or '').strip()
        if not memo:
            return self.env['account.move']

        base_domain = [
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('company_id', '=', self.company_id.id),
            '|', ('name', '=', memo), ('payment_reference', '=', memo),
        ]
        if self.partner_id:
            invoice = self.env['account.move'].search(
                [('partner_id', 'child_of', self.partner_id.commercial_partner_id.id)] + base_domain,
                limit=1,
            )
            if invoice:
                return invoice
        return self.env['account.move'].search(base_domain, limit=1)

    def _get_invoice_open_amount(self, invoice):
        self.ensure_one()
        installment_remaining = getattr(invoice, 'total_remaining_amount', 0.0) or 0.0
        invoice_residual = abs(invoice.amount_residual or 0.0)
        if invoice.installment_ids and installment_remaining > 0:
            return installment_remaining
        return invoice_residual or installment_remaining

    def _should_auto_fill_from_memo(self):
        self.ensure_one()
        return (
            self.state == 'draft'
            and self.payment_type == 'inbound'
            and self.partner_type == 'customer'
            and self.payment_scope == 'by_invoice'
            and (self.memo or '').strip()
            and self.amount
        )

    def _auto_fill_control_payment_from_memo(self):
        """Fill Transaction with the invoice referenced in memo."""
        if self.env.context.get('skip_auto_fill_control_payment'):
            return False

        filled = False
        for payment in self:
            if not payment._should_auto_fill_from_memo():
                continue

            invoice = payment._find_invoice_from_memo()
            if not invoice:
                _logger.debug(
                    "No invoice found for payment memo %r (payment %s)",
                    payment.memo,
                    payment.display_name,
                )
                continue

            open_amount = payment._get_invoice_open_amount(invoice)
            rounding = payment.currency_id.rounding if payment.currency_id else 0.01
            if float_compare(open_amount or 0.0, 0.0, precision_rounding=rounding) <= 0:
                continue

            to_pay = min(payment.amount, open_amount)
            if float_compare(to_pay, 0.0, precision_rounding=rounding) <= 0:
                continue
            if float_compare(payment.amount, open_amount, precision_rounding=rounding) > 0:
                _logger.debug(
                    "Payment amount %s exceeds open amount %s for invoice %s",
                    payment.amount,
                    open_amount,
                    invoice.name,
                )
                continue

            existing = payment.control_payment_ids.filtered(
                lambda line: line.invoice_id == invoice and line.to_pay
            )
            if existing and payment._amounts_match(existing[0].to_pay, to_pay):
                filled = True
                continue

            due_date = payment.payment_due_date_filter or payment.date or fields.Date.today()
            if due_date and hasattr(invoice, 'due_date_filter'):
                invoice.due_date_filter = due_date
                if hasattr(invoice, '_compute_due_amount'):
                    invoice._compute_due_amount()

            line_vals = {
                'invoice_id': invoice.id,
                'to_pay': to_pay,
                'due_date': due_date,
            }
            commands = [(5, 0, 0), (0, 0, line_vals)]
            if payment.id:
                payment.with_context(skip_auto_fill_control_payment=True).write({
                    'control_payment_ids': commands,
                })
            else:
                payment.control_payment_ids = commands
            filled = True
        return filled

    @api.model_create_multi
    def create(self, vals_list):
        payments = super().create(vals_list)
        payments.filtered(lambda payment: payment.state == 'draft')._auto_fill_control_payment_from_memo()
        return payments

    @api.depends('control_payment_ids.to_pay', 'amount')
    def _compute_total_control_to_pay(self):
        for payment in self:
            total = sum(payment.control_payment_ids.mapped('to_pay'))
            payment.total_control_to_pay = total
            payment.control_payment_remaining_amount = (payment.amount or 0.0) - total

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'payment_due_date_filter' in fields_list:
            if 'date' in res and res.get('date'):
                res['payment_due_date_filter'] = res['date']
            else:
                res['payment_due_date_filter'] = fields.Date.today()
        if 'control_payment_ids' not in fields_list or not res.get('partner_id'):
            return res

        payment = self.new({
            'partner_id': res.get('partner_id'),
            'partner_type': res.get('partner_type', 'customer'),
            'payment_type': res.get('payment_type', 'inbound'),
            'payment_scope': res.get('payment_scope', 'by_invoice'),
            'memo': res.get('memo'),
            'amount': res.get('amount'),
            'currency_id': res.get('currency_id'),
            'company_id': res.get('company_id') or self.env.company.id,
            'date': res.get('date') or fields.Date.today(),
            'payment_due_date_filter': res.get('payment_due_date_filter') or res.get('date') or fields.Date.today(),
            'state': 'draft',
        })
        if payment._auto_fill_control_payment_from_memo():
            res['control_payment_ids'] = [
                (0, 0, {
                    'invoice_id': line.invoice_id.id,
                    'to_pay': line.to_pay,
                    'due_date': line.due_date,
                })
                for line in payment.control_payment_ids
            ]
            return res

        invoices = self.env['account.move'].search([
            ('partner_id', 'child_of', res['partner_id']),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', '!=', 'paid'),
            ('total_remaining_amount', '!=', 0),
        ])
        due = res.get('payment_due_date_filter') or res.get('date') or fields.Date.today()
        res['control_payment_ids'] = [(0, 0, {
            'invoice_id': inv.id,
            'to_pay': 0.0,
            'due_date': due,
        }) for inv in invoices]
        return res

    @api.onchange('partner_id')
    def _onchange_partner_load_invoices(self):
        """Load unpaid invoices into control_payment_ids when partner is selected."""
        if not self.partner_id:
            self.control_payment_ids = [(5, 0, 0)]
            return

        if self._auto_fill_control_payment_from_memo():
            return

        invoices = self.env['account.move'].search([
            ('partner_id', 'child_of', self.partner_id.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', '!=', 'paid'),
            ('total_remaining_amount', '!=', 0),
        ])
        due_date_value = self.payment_due_date_filter or self.date or fields.Date.today()
        self.control_payment_ids = [(0, 0, {
            'invoice_id': inv.id,
            'to_pay': 0.0,
            'due_date': due_date_value,
        }) for inv in invoices]

    @api.onchange('date')
    def _onchange_payment_date(self):
        if self.date:
            self.payment_due_date_filter = self.date
            self._onchange_payment_due_date_filter()
            self._auto_fill_control_payment_from_memo()

    @api.onchange('payment_due_date_filter')
    def _onchange_payment_due_date_filter(self):
        if self.payment_due_date_filter:
            for line in self.control_payment_ids:
                line.due_date = self.payment_due_date_filter
                if line.invoice_id and hasattr(line.invoice_id, 'due_date_filter'):
                    line.invoice_id.due_date_filter = self.payment_due_date_filter
                    if hasattr(line.invoice_id, '_compute_due_amount'):
                        line.invoice_id._compute_due_amount()
                line._compute_due_amount()

    def write(self, vals):
        if 'date' in vals and vals.get('date'):
            vals['payment_due_date_filter'] = vals['date']
        if 'payment_due_date_filter' in vals:
            for payment in self:
                for line in payment.control_payment_ids:
                    line.due_date = vals['payment_due_date_filter']
                    if line.invoice_id and hasattr(line.invoice_id, 'due_date_filter'):
                        line.invoice_id.due_date_filter = vals['payment_due_date_filter']
                        if hasattr(line.invoice_id, '_compute_due_amount'):
                            line.invoice_id._compute_due_amount()
                    line._compute_due_amount()
        result = super().write(vals)
        if not self.env.context.get('skip_auto_fill_control_payment'):
            self.filtered(lambda payment: payment.state == 'draft')._auto_fill_control_payment_from_memo()
        # Remove control payment lines with to_pay == 0
        for payment in self:
            zero_lines = payment.control_payment_ids.filtered(lambda l: l.to_pay == 0)
            if zero_lines:
                zero_lines.unlink()
        return result

    def action_process_control_payments(self):
        self.ensure_one()
        from_action_post = self.env.context.get('from_action_post', False)

        if not self.control_payment_ids:
            if from_action_post:
                return False
            raise UserError(_("Please select at least one invoice to pay"))

        invoices_to_process = self.control_payment_ids.filtered(lambda l: l.to_pay != 0)
        if not invoices_to_process:
            if from_action_post:
                return False
            raise UserError(_("Please set To Pay amount for at least one invoice"))

        if not self.payment_due_date_filter:
            self.payment_due_date_filter = self.date or fields.Date.today()

        total_to_pay = sum(invoices_to_process.mapped('to_pay'))
        if total_to_pay != self.amount:
            if from_action_post:
                _logger.warning(
                    "Payment %s: Total control to pay (%s) != amount (%s). Skipping.",
                    self.name,
                    total_to_pay,
                    self.amount,
                )
                return False
            raise UserError(_(
                "Total control to pay amount (%s) must equal the payment amount (%s)."
            ) % (total_to_pay, self.amount))

        processed_count = 0
        errors = []

        product_filter = self.selected_product_id if self.payment_scope == 'by_invoice_lines' and self.selected_product_id else False
        payment_name = self.name or self.display_name or _('Payment')

        for line in self.control_payment_ids.filtered(lambda l: l.to_pay != 0):
            try:
                if self.payment_scope == 'by_all_invoice_lines' and line.installment_id:
                    # Installment-level payment: pay directly to this installment
                    inst = line.installment_id
                    pay_here = min(line.to_pay, inst.amount_residual)
                    prev_paid = inst.amount_paid or 0.0
                    inst.write({
                        'amount_paid': prev_paid + pay_here,
                        'paid_date': fields.Date.today(),
                        'payment_reference': (
                            f'{inst.payment_reference}, {payment_name}'
                            if inst.payment_reference else payment_name
                        ),
                    })
                    log_model = self.env.get('account.installment.payment.log')
                    if log_model and hasattr(log_model, 'create_log'):
                        log_model.create_log(
                            installment=inst,
                            payment=self,
                            paid_amount=pay_here,
                            action_type='action_pay_installments',
                        )
                    processed_count += 1
                elif self.payment_scope == 'by_product_invoice' and line.invoice_line_id:
                    # Per-product-line payment: filter by invoice_line's product
                    inv_line_product = line.invoice_line_id.product_id
                    write_vals = {
                        'due_date_filter': self.payment_due_date_filter,
                        'to_pay_amount': line.to_pay,
                        'product_filter_id': inv_line_product.id if inv_line_product else False,
                    }
                    line.invoice_id.write(write_vals)
                    before_timestamp = fields.Datetime.now()
                    line.invoice_id.with_context(payment_id=self.id).action_pay_installments()

                    log_model = self.env.get('account.installment.payment.log')
                    if log_model:
                        logs = log_model.search([
                            ('move_id', '=', line.invoice_id.id),
                            ('action_type', '=', 'action_pay_installments'),
                            ('create_date', '>=', before_timestamp),
                        ])
                        for log in logs:
                            if not log.payment_id:
                                log.write({'payment_id': self.id})
                    processed_count += 1
                else:
                    # Invoice-level payment: use existing flow
                    write_vals = {
                        'due_date_filter': self.payment_due_date_filter,
                        'to_pay_amount': line.to_pay,
                        'product_filter_id': product_filter.id if product_filter else False,
                    }
                    line.invoice_id.write(write_vals)
                    before_timestamp = fields.Datetime.now()
                    line.invoice_id.with_context(payment_id=self.id).action_pay_installments()

                    log_model = self.env.get('account.installment.payment.log')
                    if log_model:
                        logs = log_model.search([
                            ('move_id', '=', line.invoice_id.id),
                            ('action_type', '=', 'action_pay_installments'),
                            ('create_date', '>=', before_timestamp),
                        ])
                        for log in logs:
                            if not log.payment_id:
                                log.write({'payment_id': self.id})
                    processed_count += 1
            except Exception as e:
                ref = line.installment_reference or (line.invoice_id.name if line.invoice_id else '')
                errors.append("%s: %s" % (ref, str(e)))

        if errors:
            raise UserError(_("Errors while processing payments:\n%s") % '\n'.join(errors))

        if processed_count > 0:
            self._mark_invoices_paid_if_fully_paid()

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
        return False

    def _mark_invoices_paid_if_fully_paid(self):
        for line in self.control_payment_ids.filtered(lambda l: l.to_pay != 0):
            invoice = line.invoice_id
            if invoice and getattr(invoice, 'total_remaining_amount', 0) == 0:
                if invoice.payment_state != 'paid':
                    invoice.write({'payment_state': 'paid'})
                    _logger.info("Marked invoice %s as paid (total_remaining_amount = 0)", invoice.name)
