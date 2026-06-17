# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from odoo.tools import float_compare


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    installment_ids = fields.One2many(
        'account.move.installment',
        'move_id',
        string='Installments',
        copy=False
    )
    has_installments = fields.Boolean(
        string='Has Installments',
        compute='_compute_has_installments',
        store=True
    )
    total_installment_count = fields.Integer(
        string='Total Installment Count',
        compute='_compute_total_installment_count',
        store=True
    )
    paid_installment_count = fields.Integer(
        string='Paid Installments',
        compute='_compute_installment_counts',
        store=True
    )
    pending_installment_count = fields.Integer(
        string='Pending Installments',
        compute='_compute_installment_counts',
        store=True
    )
    overdue_installment_count = fields.Integer(
        string='Overdue Installments',
        compute='_compute_installment_counts',
        store=True
    )
    total_paid_amount = fields.Monetary(
        string='Total Paid Amount',
        currency_field='currency_id',
        compute='_compute_installment_totals',
        store=True
    )
    total_remaining_amount = fields.Monetary(
        string='Total Remaining Amount',
        currency_field='currency_id',
        compute='_compute_installment_totals',
        store=True
    )
    nearest_due_installment_amount = fields.Monetary(
        string='Nearest Due Installment Amount',
        currency_field='currency_id',
        compute='_compute_nearest_due_installment',
        store=True
    )
    nearest_due_installment_date = fields.Date(
        string='Nearest Due Installment Date',
        compute='_compute_nearest_due_installment',
        store=True
    )
    due_date_filter = fields.Date(
        string='Date for Pay',
        help='Select a date to calculate due amount for installments due on or before this date',
    )
    due_amount = fields.Monetary(
        string='Due Amount',
        currency_field='currency_id',
        compute='_compute_due_amount',
        help='Total remaining amount of installments due on or before the selected date',
    )
    to_pay_amount = fields.Monetary(
        string='To Pay',
        currency_field='currency_id',
        default=0.0,
        help='Amount to distribute among installments due on or before the selected date',
    )
    product_filter_id = fields.Many2one(
        'product.product',
        string='Product Filter',
        help='When set, due_amount only considers installments for this product',
    )
    apply_payment_term_per_line = fields.Boolean(
        string='Apply Payment Term Per Line',
        default=True,
        help='If enabled, each invoice line can have its own payment term. '
             'Otherwise, the payment term applies to the entire invoice.'
    )
    
    @api.onchange('invoice_payment_term_id')
    def _onchange_invoice_payment_term_scope(self):
        """Set apply_payment_term_per_line based on payment term scope"""
        if self.invoice_payment_term_id and hasattr(self.invoice_payment_term_id, 'scope'):
            self.apply_payment_term_per_line = (self.invoice_payment_term_id.scope == 'per_lines')
    
    @api.onchange('apply_payment_term_per_line', 'invoice_payment_term_id')
    def _onchange_apply_payment_term_per_line(self):
        """When enabling per-line payment terms, copy invoice payment term to all lines"""
        if self.apply_payment_term_per_line and self.invoice_payment_term_id:
            # Copy invoice payment term to all lines that don't have one
            for line in self.invoice_line_ids:
                if not line.payment_term_id and self.invoice_payment_term_id.is_installment_term:
                    line.payment_term_id = self.invoice_payment_term_id
    
    @api.depends('installment_ids')
    def _compute_has_installments(self):
        for move in self:
            move.has_installments = bool(move.installment_ids)

    def _get_total_line_first_payment_amount(self):
        """Sum of down payments configured on invoice lines (per-lines scope)."""
        self.ensure_one()
        if not self.is_invoice(include_receipts=True):
            return 0.0
        if not self.apply_payment_term_per_line and getattr(self, 'scope', False) != 'per_lines':
            return 0.0
        total = sum(
            line._get_line_first_payment_amount(line.price_total or 0.0)
            for line in self.invoice_line_ids.filtered(
                lambda item: item.display_type in (False, 'product')
            )
        )
        return self.currency_id.round(total) if self.currency_id else total

    @api.depends('installment_ids')
    def _compute_total_installment_count(self):
        for move in self:
            move.total_installment_count = len(move.installment_ids)
    
    @api.depends('installment_ids.state')
    def _compute_installment_counts(self):
        """Compute counts of installments by state"""
        for move in self:
            move.paid_installment_count = len(move.installment_ids.filtered(lambda i: i.state == 'paid'))
            move.pending_installment_count = len(move.installment_ids.filtered(
                lambda i: i.state in ('draft', 'due')
            ))
            move.overdue_installment_count = len(move.installment_ids.filtered(lambda i: i.state == 'overdue'))
    
    @api.depends('installment_ids.state', 'installment_ids.amount_paid', 'installment_ids.amount_total', 'amount_total')
    def _compute_installment_totals(self):
        """Compute total paid and remaining amounts from installments"""
        for move in self:
            # Calculate total paid amount from installments
            move.total_paid_amount = sum(move.installment_ids.mapped('amount_paid'))
            
            # Calculate total remaining amount
            move.total_remaining_amount = sum(move.installment_ids.mapped('amount_residual'))
    
    @api.depends('installment_ids', 'installment_ids.state', 'installment_ids.date_due', 'installment_ids.amount_residual')
    def _compute_nearest_due_installment(self):
        """Compute the installment with nearest due date that is not fully paid"""
        for move in self:
            move.nearest_due_installment_amount = 0.0
            move.nearest_due_installment_date = False
            
            if not move.installment_ids:
                continue
            
            # Get all installments that are not fully paid
            unpaid_installments = move.installment_ids.filtered(
                lambda i: i.state in ('draft', 'due', 'partial', 'overdue') and i.amount_residual > 0
            )
            
            if not unpaid_installments:
                continue
            
            # Sort by due date (ascending - nearest first)
            sorted_installments = unpaid_installments.sorted(key=lambda i: i.date_due)
            
            if sorted_installments:
                nearest = sorted_installments[0]
                move.nearest_due_installment_amount = nearest.amount_residual
                move.nearest_due_installment_date = nearest.date_due

    @api.depends(
        'due_date_filter',
        'product_filter_id',
        'installment_ids',
        'installment_ids.state',
        'installment_ids.date_due',
        'installment_ids.amount_residual',
        'installment_ids.product_id',
    )
    def _compute_due_amount(self):
        """Total remaining amount of installments due on or before due_date_filter.
        When product_filter_id is set, only installments for that product are considered."""
        for move in self:
            if not move.due_date_filter or not move.installment_ids:
                move.due_amount = 0.0
                continue
            eligible = move.installment_ids.filtered(
                lambda i: i.state in ('draft', 'due', 'partial', 'overdue')
                and i.amount_residual > 0
                and i.date_due
                and i.date_due <= move.due_date_filter
            )
            if move.product_filter_id:
                eligible = eligible.filtered(
                    lambda i: i.product_id.id == move.product_filter_id.id
                )
            move.due_amount = sum(eligible.mapped('amount_residual'))

    def action_pay_installments(self):
        """Distribute to_pay_amount among installments due on or before due_date_filter.
        When product_filter_id is set, only pays installments for that product."""
        self.ensure_one()
        if not self.to_pay_amount or self.to_pay_amount <= 0:
            raise UserError(_('Please enter a valid amount to pay.'))
        if not self.due_date_filter:
            raise UserError(_('Please select a date for pay first.'))

        eligible = self.installment_ids.filtered(
            lambda i: i.state in ('draft', 'due', 'partial', 'overdue')
            and i.amount_residual > 0
            and i.date_due
            and i.date_due <= self.due_date_filter
        )
        if self.product_filter_id:
            eligible = eligible.filtered(
                lambda i: i.product_id.id == self.product_filter_id.id
            )
        if not eligible:
            raise UserError(_('No installments found due on or before the selected date.'))

        partial_first = eligible.filtered(lambda i: i.state == 'partial')
        others = eligible.filtered(lambda i: i.state != 'partial')
        sorted_installments = partial_first.sorted(key=lambda i: i.date_due) | others.sorted(key=lambda i: i.date_due)

        payment_id = self.env.context.get('payment_id')
        payment = self.env['account.payment'].browse(payment_id) if payment_id else None
        payment_name = (payment.name or payment.display_name or _('Payment')) if payment else _('Manual')

        remaining_to_pay = self.to_pay_amount
        for inst in sorted_installments:
            if remaining_to_pay <= 0:
                break
            need = inst.amount_residual
            pay_here = min(remaining_to_pay, need)
            prev_paid = inst.amount_paid or 0.0
            new_paid = prev_paid + pay_here

            inst.write({
                'amount_paid': new_paid,
                'paid_date': fields.Date.today(),
                'payment_reference': (inst.payment_reference or '') and f'{inst.payment_reference}, {payment_name}' or payment_name,
            })

            self.env['account.installment.payment.log'].create_log(
                installment=inst,
                payment=payment,
                paid_amount=pay_here,
                action_type='action_pay_installments',
            )
            remaining_to_pay -= pay_here

        self.to_pay_amount = 0.0
        self._compute_due_amount()
        self._compute_installment_counts()
        self._compute_installment_totals()
        self._compute_nearest_due_installment()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _create_installments_from_payment_term(self):
        """
        Create installments from payment term line_ids when is_installment_term = True.
        This method is called when the invoice is created or when payment term is changed.
        Supports both per-invoice and per-line payment terms.
        """
        for move in self:
            # Only process invoices
            if not move.is_invoice(include_receipts=True):
                continue
            
            # Delete existing installments to regenerate
            if move.installment_ids:
                move.installment_ids.unlink()
            
            # Check if applying payment term per line
            if move.apply_payment_term_per_line:
                # Process each invoice line separately
                self._create_installments_per_line(move)
            else:
                # Process invoice as a whole
                self._create_installments_for_invoice(move)
    
    def _create_installments_for_invoice(self, move):
        """Create installments for the entire invoice"""
        # Check if payment term has is_installment_term = True
        if not move.invoice_payment_term_id or not move.invoice_payment_term_id.is_installment_term:
            return
        
        # Get payment term lines
        payment_term = move.invoice_payment_term_id
        if not payment_term.line_ids:
            return
        
        # Calculate total invoice amount
        total_amount = move.amount_total
        if move.currency_id != move.company_id.currency_id:
            # Convert to invoice currency
            total_amount = move.amount_total_in_currency_signed
        else:
            total_amount = abs(move.amount_total_signed)
        
        # Get invoice date or use today
        date_ref = move.invoice_date or move.date or fields.Date.today()
        
        # Create installments from payment term lines
        installments = self._calculate_installments_from_term(
            payment_term, total_amount, date_ref, move, line_name='Invoice Total'
        )
        
        # Create installments
        # Only create if move_id exists (invoice is saved)
        if installments and move.id:
            for inst in installments:
                inst['move_id'] = move.id
            self.env['account.move.installment'].create(installments)
    
    def _create_installments_per_line(self, move):
        """
        Create installments for each invoice line that has a payment term.
        Each line's payment term is applied to its total price (price_total).
        """
        # Get invoice date or use today
        date_ref = move.invoice_date or move.date or fields.Date.today()
        
        # Process each invoice line
        for line in move.invoice_line_ids:
            # Skip if line doesn't have a payment term
            if not line.payment_term_id:
                continue
            
            # Skip if payment term is not an installment term
            if not line.payment_term_id.is_installment_term:
                continue
            
            # Use price_total (total price including taxes) for the line
            # This is the total amount that should be split into installments
            line_amount = line.price_total
            
            # Skip if amount is zero
            if float_compare(line_amount, 0.0, precision_digits=2) == 0:
                continue
            
            # Create installments for this line using its payment_term_id
            installments = self._calculate_installments_from_term(
                line.payment_term_id, 
                line_amount, 
                date_ref, 
                move,
                line_name=line.name or f'Line {line.sequence}'
            )
            
            # Create installments and link them to the invoice line
            # Only create if move_id exists (invoice is saved)
            if installments and move.id:
                for inst in installments:
                    inst['move_id'] = move.id
                    inst['invoice_line_id'] = line.id
                self.env['account.move.installment'].create(installments)
    
    def _calculate_installments_from_term(self, payment_term, amount, date_ref, move, line_name=''):
        """Calculate installments from a payment term for a given amount"""
        if not payment_term.line_ids:
            return []
        
        installments = []
        sequence = 1
        
        for term_line in payment_term.line_ids:
            # Calculate due date
            due_date = term_line._get_due_date(date_ref)
            
            # Calculate installment amount
            if term_line.value == 'percent':
                installment_amount = amount * (term_line.value_amount / 100.0)
            elif term_line.value == 'fixed':
                # For fixed amounts, convert to invoice currency if needed
                if move.currency_id != move.company_id.currency_id:
                    # Convert fixed amount to invoice currency
                    installment_amount = move.company_id.currency_id._convert(
                        term_line.value_amount,
                        move.currency_id,
                        move.company_id,
                        date_ref
                    )
                else:
                    installment_amount = term_line.value_amount
            else:
                continue
            
            # Round amount
            installment_amount = move.currency_id.round(installment_amount)
            
            # Create installment data
            installment_name = f'{line_name} - Installment {sequence}' if line_name else f'Installment {sequence}'
            installments.append({
                'name': installment_name,
                'sequence': sequence,
                'amount_total': installment_amount,
                'date_due': due_date,
                'payment_term_line_id': term_line.id,
                'state': 'draft',
            })
            sequence += 1
        
        # Adjust last installment to ensure total matches amount exactly
        if installments:
            total_installments = sum(inst['amount_total'] for inst in installments)
            difference = amount - total_installments
            # Only adjust if difference is significant (more than 0.01)
            if float_compare(abs(difference), 0.01, precision_digits=2) > 0:
                installments[-1]['amount_total'] += difference
                installments[-1]['amount_total'] = move.currency_id.round(installments[-1]['amount_total'])
        
        return installments
    
    @api.model
    def create(self, vals):
        """Override create to auto-create installments"""
        self._sync_per_line_flag_from_scope(vals)
        vals.setdefault('apply_payment_term_per_line', vals.get('scope', 'per_lines') == 'per_lines')

        move = super().create(vals)
        
        if (
            not self.env.context.get('skip_line_payment_term_generation')
            and move.is_invoice(include_receipts=True)
            and move.apply_payment_term_per_line
        ):
            move._update_invoice_line_payment_terms_from_values()

        # Create installments if payment term is installment term
        if move.is_invoice(include_receipts=True):
            move._create_installments_from_payment_term()
        
        return move

    def _sync_per_line_flag_from_scope(self, vals):
        if vals.get('scope') == 'per_invoice':
            vals['apply_payment_term_per_line'] = False
        elif vals.get('scope') == 'per_lines':
            vals['apply_payment_term_per_line'] = True

    def _get_invoice_line_term_update_ids_from_commands(self, commands):
        line_fields = {
            'line_installment_count',
            'line_first_payment_type',
            'line_first_payment_percentage',
        }
        line_ids = set()
        include_new_lines = False
        for command in commands or []:
            if not isinstance(command, (list, tuple)) or len(command) < 3:
                continue
            operation, line_id, values = command[0], command[1], command[2]
            if not isinstance(values, dict) or not (line_fields & values.keys()):
                continue
            if operation == 1 and line_id:
                line_ids.add(line_id)
            elif operation == 0:
                include_new_lines = True
        return line_ids, include_new_lines

    def _update_invoice_line_payment_terms_from_values(self, line_ids=None, include_new_lines=False):
        for move in self.filtered(lambda item: item.is_invoice(include_receipts=True) and item.apply_payment_term_per_line):
            lines = move.invoice_line_ids.filtered(lambda line: line.display_type in (False, 'product'))
            if line_ids is not None:
                lines = lines.filtered(lambda line: line.id in line_ids or (include_new_lines and line.id not in line_ids))
            lines._generate_line_payment_terms_from_values()
    
    def write(self, vals):
        """Override write to recreate installments when payment term changes"""
        vals = dict(vals)
        self._sync_per_line_flag_from_scope(vals)
        line_ids_to_update = None
        include_new_lines = False
        if 'invoice_line_ids' in vals:
            line_ids_to_update, include_new_lines = self._get_invoice_line_term_update_ids_from_commands(
                vals.get('invoice_line_ids')
            )

        # Sync apply_payment_term_per_line from payment term scope when invoice_payment_term_id changes
        if 'invoice_payment_term_id' in vals and vals.get('invoice_payment_term_id'):
            payment_term = self.env['account.payment.term'].browse(vals['invoice_payment_term_id'])
            if payment_term and hasattr(payment_term, 'scope'):
                vals['apply_payment_term_per_line'] = (payment_term.scope == 'per_lines')
        elif 'invoice_payment_term_id' in vals and not vals.get('invoice_payment_term_id'):
            vals['apply_payment_term_per_line'] = False

        result = super().write(vals)
        if 'invoice_line_ids' in vals:
            for move in self:
                if move.is_invoice(include_receipts=True) and move.apply_payment_term_per_line:
                    if line_ids_to_update or include_new_lines:
                        move._update_invoice_line_payment_terms_from_values(line_ids_to_update, include_new_lines)
        
        # Check if payment term, invoice date, or per-line option changed
        fields_to_check = [
            'invoice_payment_term_id', 
            'invoice_date', 
            'date', 
            'amount_total',
            'apply_payment_term_per_line'
        ]
        if any(field in vals for field in fields_to_check):
            for move in self:
                if move.is_invoice(include_receipts=True):
                    # If enabling per-line payment terms, copy invoice payment term to lines
                    if 'apply_payment_term_per_line' in vals and vals['apply_payment_term_per_line']:
                        if move.invoice_payment_term_id and move.invoice_payment_term_id.is_installment_term:
                            # Update all lines to have the invoice payment term if they don't have one
                            for line in move.invoice_line_ids:
                                if not line.payment_term_id:
                                    line.payment_term_id = move.invoice_payment_term_id
                    
                    # Delete existing installments
                    if move.installment_ids:
                        move.installment_ids.unlink()
                    
                    # Only create installments if invoice is posted (confirmed)
                    # Otherwise, installments will be created when posting
                    if move.state == 'posted':
                        # Recreate installments
                        move._create_installments_from_payment_term()
        
        # Check if invoice line payment terms changed (when per-line is enabled)
        if 'invoice_line_ids' in vals:
            for move in self:
                if move.is_invoice(include_receipts=True) and move.apply_payment_term_per_line:
                    # Delete existing installments
                    if move.installment_ids:
                        move.installment_ids.unlink()
                    # Only create installments if invoice is posted (confirmed)
                    if move.state == 'posted':
                        # Recreate installments
                        move._create_installments_from_payment_term()

        if vals.get('payment_state') == 'paid':
            self.filtered(
                lambda move: move.is_invoice(include_receipts=True) and move.has_installments
            )._sync_installments_on_invoice_paid()

        return result

    def _write_multi(self, vals_list):
        """Sync installments when payment_state is flushed to the database."""
        sync_moves = self.env['account.move']
        for move, vals in zip(self, vals_list):
            if (
                vals.get('payment_state') == 'paid'
                and move.is_invoice(include_receipts=True)
                and move.installment_ids
            ):
                sync_moves |= move
        result = super()._write_multi(vals_list)
        if sync_moves:
            sync_moves._sync_installments_on_invoice_paid()
        return result

    def _get_invoice_installment_payment(self):
        """Return the payment record that settled the invoice, if any."""
        self.ensure_one()
        payments = self._get_reconciled_payments().filtered(
            lambda payment: payment.state in ('in_process', 'paid')
        )
        if not payments:
            return self.env['account.payment']
        return payments.sorted(key=lambda payment: payment.date, reverse=True)[0]

    def _get_invoice_installment_payment_date(self):
        """Payment date used when syncing installments after the invoice is paid."""
        self.ensure_one()
        payment = self._get_invoice_installment_payment()
        if payment:
            return payment.date
        counterparty_lines = self._get_reconciled_amls().filtered(
            lambda aml: aml.move_id.id != self.id
        )
        if counterparty_lines:
            return max(counterparty_lines.mapped('date'))
        return self.invoice_date or self.date or fields.Date.today()

    def _get_invoice_installment_payment_reference(self):
        self.ensure_one()
        payments = self._get_reconciled_payments().filtered(
            lambda payment: payment.state in ('in_process', 'paid')
        )
        refs = [name for name in payments.mapped('name') if name]
        return ', '.join(refs)

    def _sync_installments_on_invoice_paid(self):
        """Mark all unpaid installments as paid when the invoice becomes paid."""
        if self.env.context.get('skip_installment_invoice_paid_sync'):
            return

        log_model = self.env.get('account.installment.payment.log')
        for move in self:
            if move.payment_state != 'paid' or not move.installment_ids:
                continue

            unpaid_installments = move.installment_ids.filtered(
                lambda inst: float_compare(
                    inst.amount_residual or 0.0,
                    0.0,
                    precision_rounding=move.currency_id.rounding,
                ) > 0
            )
            if not unpaid_installments:
                continue

            payment_date = move._get_invoice_installment_payment_date()
            payment_ref = move._get_invoice_installment_payment_reference()
            payment = move._get_invoice_installment_payment()

            for installment in unpaid_installments:
                paid_amount = installment.amount_residual
                installment.write({
                    'amount_paid': installment.amount_total,
                    'paid_date': payment_date,
                    'payment_reference': payment_ref or installment.payment_reference,
                })
                if log_model and paid_amount:
                    log_model.create_log(
                        installment=installment,
                        payment=payment,
                        paid_amount=paid_amount,
                        action_type='invoice_paid_sync',
                    )
    
    def action_post(self):
        """Override action_post to create installments and update installment states"""
        result = super().action_post()
        
        # Create installments if they don't exist yet (for installment payment terms)
        for move in self:
            if move.is_invoice(include_receipts=True):
                # Per-line invoices may not have a global invoice_payment_term_id.
                if move.apply_payment_term_per_line:
                    if not move.installment_ids:
                        move._create_installments_from_payment_term()
                elif move.invoice_payment_term_id and move.invoice_payment_term_id.is_installment_term:
                    # Create installments if they don't exist
                    if not move.installment_ids:
                        move._create_installments_from_payment_term()
                
                # Update installment states when invoice is posted
                if move.has_installments:
                    for installment in move.installment_ids:
                        installment._compute_state()
        
        return result

