# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _is_installment_product_line(self):
        self.ensure_one()
        return self.display_type in (False, 'product')
    
    @api.depends('product_id', 'move_id.ref', 'move_id.payment_reference', 'display_type', 'move_id.name')
    def _compute_name(self):
        """Override: For payment_term lines, use invoice name only (no 'installment #1' suffix)."""
        # Process payment_term lines - use invoice name only, no "installment #1"
        payment_term_lines = self.filtered(lambda l: l.display_type == 'payment_term' and l.move_id.is_invoice(True))
        for line in payment_term_lines:
            line.name = line.move_id.name or line.move_id.payment_reference or ''
        
        # Call super for remaining lines (product lines, etc.)
        super(AccountMoveLine, self - payment_term_lines)._compute_name()
    
    payment_term_id = fields.Many2one(
        'account.payment.term',
        string='Payment Term',
        help='Payment term for this invoice line. Only used when "Apply Payment Term Per Line" is enabled on the invoice.',
        domain="[('is_installment_term', '=', True)]"
    )
    line_installment_count = fields.Integer(
        string='Installments Num.',
        default=0,
    )
    line_first_payment_type = fields.Selection(
        [
            ('percent', 'Percent'),
            ('fixed', 'Fixed'),
        ],
        string='First Payment Type',
        default='fixed',
    )
    line_first_payment_percentage = fields.Float(
        string='First Payment',
        default=0.0,
    )
    line_sal_no = fields.Integer(
        string='Sal No.',
        help='Sale number entered by the user for this invoice line.',
    )
    line_due_amount = fields.Monetary(
        string='Due Amt.',
        compute='_compute_line_payment_amounts',
        currency_field='currency_id',
        help='Total amount minus the first payment.',
    )
    line_installment_amount = fields.Monetary(
        string='Inst. Amt.',
        compute='_compute_line_payment_amounts',
        currency_field='currency_id',
        help='Amount of the first installment after the first payment.',
    )

    @api.depends(
        'price_total',
        'line_first_payment_type',
        'line_first_payment_percentage',
        'line_installment_count',
        'payment_term_id',
        'payment_term_id.line_ids',
        'currency_id',
        'move_id.invoice_date',
        'move_id.date',
    )
    def _compute_line_payment_amounts(self):
        for line in self:
            total = line.price_total or 0.0
            if line.payment_term_id:
                move = line.move_id
                date_ref = move.invoice_date or move.date or fields.Date.today()
                breakdown = line.payment_term_id.get_line_payment_amount_breakdown(
                    total,
                    currency=line.currency_id,
                    company=line.company_id,
                    date_ref=date_ref,
                )
                line.line_due_amount = breakdown['due_amount']
                line.line_installment_amount = breakdown['first_installment_amount']
                continue
            first_pay = line._get_line_first_payment_amount(total)
            line.line_due_amount = total - first_pay
            line.line_installment_amount = line._get_line_first_installment_amount(total, first_pay)

    def _get_line_first_payment_amount(self, total):
        self.ensure_one()
        if not total:
            return 0.0
        if self.line_first_payment_type == 'fixed':
            return min(self.line_first_payment_percentage or 0.0, total)
        pct = self.line_first_payment_percentage or 0.0
        return total * (pct / 100.0)

    def _get_line_first_installment_amount(self, total, first_pay):
        """First scheduled installment (after down payment), aligned with payment term split."""
        self.ensure_one()
        count = self.line_installment_count or 0
        if not total or count < 1:
            return 0.0
        if self.line_first_payment_type == 'percent':
            remaining_pct = max(0.0, 100.0 - (self.line_first_payment_percentage or 0.0))
            inst_pct = remaining_pct / count
            return total * (inst_pct / 100.0)
        remaining = max(0.0, total - first_pay)
        return remaining / count

    @api.model_create_multi
    def create(self, vals_list):
        generate_flags = [
            any(
                field in vals
                for field in ('line_installment_count', 'line_first_payment_type', 'line_first_payment_percentage')
            )
            for vals in vals_list
        ]
        for vals in vals_list:
            self._sync_line_plan_values_from_term(vals)
        lines = super().create(vals_list)
        if not self.env.context.get('skip_line_payment_term_generation'):
            lines_to_generate = lines.filtered(lambda line: generate_flags[lines.ids.index(line.id)])
            lines_to_generate._generate_line_payment_terms_from_values()
        return lines

    def write(self, vals):
        vals = dict(vals)
        should_generate = any(
            field in vals
            for field in ('line_installment_count', 'line_first_payment_type', 'line_first_payment_percentage')
        )
        self._sync_line_plan_values_from_term(vals)
        result = super().write(vals)
        if not self.env.context.get('skip_line_payment_term_generation') and should_generate:
            self._generate_line_payment_terms_from_values()
        if should_generate and hasattr(self, '_recompute_price_from_invoice_pricelist'):
            self._recompute_price_from_invoice_pricelist()
        return result

    def _get_plan_values_from_payment_term(self, payment_term):
        """Derive line installment fields from a payment term (incl. custom schedules)."""
        if not payment_term or not payment_term.is_installment_term:
            return {}

        if payment_term.pay_type == 'custom':
            term_lines = payment_term.line_ids.sorted(key=lambda line: (line.nb_days, line.id))
            if not term_lines:
                return {
                    'line_installment_count': 0,
                    'line_first_payment_type': payment_term.first_payment_type or 'percent',
                    'line_first_payment_percentage': payment_term.first_payment_percentage or 0.0,
                }

            if payment_term.first_payment_percentage and payment_term.first_payment_percentage > 0:
                installment_lines = term_lines.filtered(lambda line: line.nb_days > 0)
                installment_count = len(installment_lines) or max(len(term_lines) - 1, 0)
                return {
                    'line_installment_count': installment_count,
                    'line_first_payment_type': payment_term.first_payment_type or 'percent',
                    'line_first_payment_percentage': payment_term.first_payment_percentage,
                }

            first_line = term_lines[0]
            if len(term_lines) > 1 and first_line.nb_days == 0:
                return {
                    'line_installment_count': len(term_lines) - 1,
                    'line_first_payment_type': first_line.value,
                    'line_first_payment_percentage': first_line.value_amount,
                }

            return {
                'line_installment_count': len(term_lines),
                'line_first_payment_type': 'percent',
                'line_first_payment_percentage': 0.0,
            }

        return {
            'line_installment_count': payment_term.installment_count or 0,
            'line_first_payment_type': payment_term.first_payment_type or 'fixed',
            'line_first_payment_percentage': payment_term.first_payment_percentage or 0.0,
        }

    def _sync_line_plan_values_from_term(self, vals):
        if not vals.get('payment_term_id'):
            return
        payment_term = self.env['account.payment.term'].browse(vals['payment_term_id'])
        if not payment_term.exists():
            return
        plan_values = self._get_plan_values_from_payment_term(payment_term)
        for key, value in plan_values.items():
            vals.setdefault(key, value)

    def _get_base_invoice_payment_term(self):
        self.ensure_one()
        return self.move_id.invoice_payment_term_id

    def _get_line_payment_term_values(self):
        self.ensure_one()
        base_term = self._get_base_invoice_payment_term()
        line_term = self.payment_term_id
        return {
            'pay_type': (
                line_term.pay_type
                if line_term
                else (base_term.pay_type if base_term else False) or self.move_id.pay_type or 'fixed'
            ),
            'installment_count': self.line_installment_count,
            'first_payment_type': self.line_first_payment_type or (base_term.first_payment_type if base_term else 'fixed'),
            'first_payment_percentage': self.line_first_payment_percentage,
            'baseline_date': (base_term.baseline_date if base_term else False) or self.move_id.baseline_date or 'invoice_date',
            'settlement_trigger': (base_term.settlement_trigger if base_term else False) or self.move_id.settlement_trigger or 'cia',
            'installment_frequency': (
                base_term.installment_frequency
                if base_term and base_term.pay_type == 'fixed'
                else self.move_id.installment_frequency
            ) or 'monthly',
            'line_amount': self.price_total,
        }

    def _build_line_payment_term_commands(self, term_values):
        self.ensure_one()
        pay_type = term_values['pay_type']
        installment_count = int(term_values['installment_count'] or 0)
        first_payment_type = term_values['first_payment_type']
        first_payment = term_values['first_payment_percentage'] or 0.0
        line_amount = term_values.get('line_amount') or 0.0

        if first_payment_type == 'percent' and not (0 <= first_payment <= 100):
            raise ValidationError(_("First Payment (%) must be between 0 and 100."))

        if pay_type == 'spot':
            return [(0, 0, {
                'value': 'percent',
                'value_amount': 100.0,
                'nb_days': 0,
                'delay_type': 'days_after',
            })]

        if pay_type != 'fixed' or installment_count < 1:
            return [(0, 0, {
                'value': 'percent',
                'value_amount': 100.0,
                'nb_days': 0,
                'delay_type': 'days_after',
            })]

        lines = []
        percent_so_far = 0.0
        if first_payment > 0:
            if first_payment_type == 'fixed':
                first_pct = (
                    round((min(first_payment, line_amount) / line_amount) * 100.0, 6)
                    if line_amount
                    else 0.0
                )
            else:
                first_pct = first_payment
            if first_pct > 0:
                lines.append((0, 0, {
                    'value': 'percent',
                    'value_amount': first_pct,
                    'nb_days': 0,
                    'delay_type': 'days_after',
                }))
                percent_so_far = first_pct

        if installment_count < 1:
            return lines or [(0, 0, {
                'value': 'percent',
                'value_amount': 100.0,
                'nb_days': 0,
                'delay_type': 'days_after',
            })]

        frequency = term_values['installment_frequency']
        days_map = {
            'monthly': 30,
            'weekly': 7,
            'daily': 1,
        }
        days_interval = days_map.get(frequency, 30)
        remaining_pct = max(100.0 - percent_so_far, 0.0)
        base_pct = round(remaining_pct / installment_count, 6) if installment_count else 0.0

        for index in range(installment_count):
            if index == installment_count - 1:
                value_amount = round(100.0 - percent_so_far, 6)
            else:
                value_amount = base_pct
                percent_so_far = round(percent_so_far + value_amount, 6)
            lines.append((0, 0, {
                'value': 'percent',
                'value_amount': value_amount,
                'nb_days': (index + 1) * days_interval,
                'delay_type': 'days_after',
            }))
        return lines

    def _payment_term_matches_line_values(self):
        self.ensure_one()
        term = self.payment_term_id
        if not term or not term.is_installment_term:
            return False
        expected = self._get_plan_values_from_payment_term(term)
        return (
            self.line_installment_count == expected.get('line_installment_count', 0)
            and self.line_first_payment_type == expected.get('line_first_payment_type')
            and float_compare(
                self.line_first_payment_percentage or 0.0,
                expected.get('line_first_payment_percentage', 0.0),
                precision_digits=2,
            ) == 0
        )

    def _generate_line_payment_terms_from_values(self):
        PaymentTerm = self.env['account.payment.term']
        for line in self.filtered(lambda item: item.move_id.apply_payment_term_per_line and item._is_installment_product_line()):
            if line.move_id.state != 'draft':
                continue
            if line._payment_term_matches_line_values():
                continue
            if line.payment_term_id and line.payment_term_id.pay_type == 'custom':
                continue
            base_term = line._get_base_invoice_payment_term()
            term_values = line._get_line_payment_term_values()
            term_vals = {
                'company_id': line.company_id.id,
                'is_installment_term': True,
                'pay_type': term_values['pay_type'],
                'installment_count': term_values['installment_count'],
                'first_payment_type': term_values['first_payment_type'],
                'first_payment_percentage': term_values['first_payment_percentage'],
                'baseline_date': term_values['baseline_date'],
                'settlement_trigger': term_values['settlement_trigger'],
                'scope': 'per_lines',
                'installment_frequency': term_values['installment_frequency'],
                'line_ids': line._build_line_payment_term_commands(term_values),
            }
            term_preview = PaymentTerm.new(term_vals)
            term_vals['name'] = term_preview._generate_auto_name() or _(
                "Line Installments - %s"
            ) % (line.name or line.move_id.name or _("Invoice Line"))
            if base_term:
                term_vals['name'] = _("%s - %s") % (base_term.name, line.name or _("Invoice Line"))
            term = PaymentTerm.create(term_vals)
            line.with_context(skip_line_payment_term_generation=True).payment_term_id = term

    def action_generate_line_payment_term(self):
        """Compatibility for stale views; generates the line term from invoice term values."""
        self._generate_line_payment_terms_from_values()
        return {'type': 'ir.actions.client', 'tag': 'reload'}
    
    @api.onchange('payment_term_id')
    def _onchange_payment_term_id(self):
        """
        Handle payment term change on invoice line.
        Don't create installments in draft state - they will be created on post.
        """
        if self.payment_term_id:
            self.line_installment_count = self.payment_term_id.installment_count
            self.line_first_payment_type = self.payment_term_id.first_payment_type
            self.line_first_payment_percentage = self.payment_term_id.first_payment_percentage
        if self.move_id and self.move_id.apply_payment_term_per_line:
            # Only delete existing installments if invoice is posted
            # In draft state, installments will be created when posting
            if self.move_id.state == 'posted' and self.move_id.installment_ids:
                # Delete existing installments and recreate
                self.move_id.installment_ids.unlink()
                self.move_id._create_installments_from_payment_term()

    @api.onchange('line_installment_count', 'line_first_payment_type', 'line_first_payment_percentage')
    def _onchange_line_payment_term_values(self):
        for line in self:
            if line.payment_term_id and not line._payment_term_matches_line_values():
                line.payment_term_id = False
        if hasattr(self, '_recompute_price_from_invoice_pricelist'):
            self.filtered('move_id')._recompute_price_from_invoice_pricelist()

