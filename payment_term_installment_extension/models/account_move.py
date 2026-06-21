# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class AccountMove(models.Model):
    _inherit = 'account.move'

    _PAYMENT_PLAN_TO_PAY_TYPE = {
        'immediate': 'spot',
        'regular': 'fixed',
        'irregular': 'custom',
    }
    _PAYMENT_PLAN_MOVE_TYPES = ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt')
    _ACCOUNT_PAYMENT_DIRECTION_TYPES = ('inbound', 'outbound')

    def _sanitize_payment_plan_type(self, vals):
        """Ignore account.payment direction values leaking via default_payment_type context."""
        vals = dict(vals)
        payment_type = vals.get('payment_type')
        move_type = vals.get('move_type') or self.env.context.get('default_move_type')
        if payment_type in self._ACCOUNT_PAYMENT_DIRECTION_TYPES:
            vals.pop('payment_type', None)
        elif move_type and move_type not in self._PAYMENT_PLAN_MOVE_TYPES:
            vals.pop('payment_type', None)
        return vals

    payment_type = fields.Selection(
        [
            ('immediate', 'Spot(Full)'),
            ('regular', 'Fixed(Auto)'),
            ('irregular', 'Custom(Manual)'),
        ],
        string="Payment plan",
        default="regular",
        tracking=True,
        copy=False,
        help="Select the payment plan for this order"
    )

    installment_count = fields.Integer(
        string="Installments Num.",
        default=0,
        copy=False,
        help="Number of installments for this payment term"
    )

    first_payment_type = fields.Selection(
        [
            ('percent', 'Percent'),
            ('fixed', 'Fixed'),
        ],
        string="First Payment Type",
        default='fixed',
        copy=False,
        help="Type of first payment: percent or fixed amount",
    )

    first_payment_percentage = fields.Float(
        string="First Payment",
        default=0.0,
        digits=(16, 2),
        copy=False,
        help="first payment",
    )
    show_installment_scope = fields.Boolean(compute='_compute_installment_config_visibility')
    readonly_installment_scope = fields.Boolean(compute='_compute_installment_config_visibility')
    show_installment_baseline_date = fields.Boolean(compute='_compute_installment_config_visibility')
    readonly_installment_baseline_date = fields.Boolean(compute='_compute_installment_config_visibility')

    scope = fields.Selection([
        ('per_invoice', 'Per Invoice'),
        ('per_lines', 'Per Lines'),
    ], string="Scope",
        default=lambda self: self.env['installment.config.mixin']._get_installment_default_scope(),
        help="Scope of payment term application")

    baseline_date = fields.Selection(
        [
            ('invoice_date', 'Invoice Date'),
            ('posting_date', 'Posting Date'),
            ('receipt_date', 'Receipt Date'),
        ],
        string="Baseline Date",
        default=lambda self: self.env['installment.config.mixin']._get_installment_default_baseline_date(),
        copy=False,
        help="Baseline date for payment term calculation",
    )

    pay_type = fields.Selection(
        [
            ('spot', 'Spot(Full)'),
            ('fixed', 'Fixed(Auto)'),
            ('custom', 'Custom(Manual)'),
        ],
        string="Payment Plan",
        default='fixed',
        copy=False,
        help="Type of payment plan",
    )
    settlement_trigger = fields.Selection(
        [
            ('cia', 'CIA-Cash in Advance'),
            ('cod', 'Cash on Delivery'),
            ('cbd', 'Cash Before Delivery'),
        ],
        string="Payment Timing",
        default='cia',
        copy=False,
        help="Settlement trigger type for spot payment plans",
    )
    installment_frequency = fields.Selection(
        [
            ('monthly', 'Monthly'),
            ('weekly', 'Weekly'),
            ('daily', 'Daily'),
        ],
        string="Installment Frequency",
        default='monthly',
        copy=False,
        help="Frequency of installments for fixed payment plans",
    )

    def _compute_installment_config_visibility(self):
        states = self.env['installment.config.mixin']._get_installment_field_ui_states()
        for move in self:
            move.show_installment_scope = states['show_installment_scope']
            move.readonly_installment_scope = states['readonly_installment_scope']
            move.show_installment_baseline_date = states['show_installment_baseline_date']
            move.readonly_installment_baseline_date = states['readonly_installment_baseline_date']

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res = self._sanitize_payment_plan_type(res)
        move_type = res.get('move_type') or self.env.context.get('default_move_type')
        if move_type in self._PAYMENT_PLAN_MOVE_TYPES:
            res = self.env['installment.config.mixin']._apply_installment_config_defaults(fields_list, res)
        return res

    def _vals_spot_first_payment(self, vals):
        """Spot plan: first payment is full amount as percent (100)."""
        vals = dict(vals)
        if vals.get('pay_type') == 'spot':
            vals['first_payment_type'] = 'percent'
            vals['first_payment_percentage'] = 100.0
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        prepared_vals_list = []
        for vals in vals_list:
            vals = self._sanitize_payment_plan_type(vals)
            move_type = vals.get('move_type')
            if move_type in self._PAYMENT_PLAN_MOVE_TYPES:
                vals.setdefault('scope', self.env['installment.config.mixin']._get_installment_default_scope())
                payment_type = vals.get('payment_type') or 'regular'
                if payment_type in self._PAYMENT_PLAN_TO_PAY_TYPE and 'pay_type' not in vals:
                    vals['pay_type'] = self._PAYMENT_PLAN_TO_PAY_TYPE[payment_type]
                vals.update(self._vals_spot_first_payment(vals))
            prepared_vals_list.append(vals)
        moves = super().create(prepared_vals_list)
        if self.env.context.get('skip_auto_generate_payment_term'):
            return moves
        # Auto-run the same generation logic after invoice creation.
        for vals, move in zip(prepared_vals_list, moves):
            if vals.get('invoice_payment_term_id') or move._invoice_payment_term_matches_plan_values():
                continue
            if not (move.state == 'draft' and move.move_type in self._PAYMENT_PLAN_MOVE_TYPES and move.scope != 'per_lines'):
                continue
            try:
                move.generate_regular_payment_term()
            except UserError:
                # Keep invoice creation non-blocking when plan data is still incomplete.
                pass
        return moves

    def write(self, vals):
        vals = dict(vals)
        vals = self._sanitize_payment_plan_type(vals)
        payment_type = vals.get('payment_type')
        if payment_type in self._PAYMENT_PLAN_TO_PAY_TYPE and 'pay_type' not in vals:
            vals['pay_type'] = self._PAYMENT_PLAN_TO_PAY_TYPE[payment_type]
        if vals.get('pay_type') == 'spot':
            vals.update(self._vals_spot_first_payment(vals))
        if vals.get('scope') == 'per_invoice':
            vals['apply_payment_term_per_line'] = False
        elif vals.get('scope') == 'per_lines':
            vals['apply_payment_term_per_line'] = True
        result = super().write(vals)
        # Auto-run on save for draft invoices/receipts.
        if not self.env.context.get('skip_auto_generate_payment_term'):
            for move in self.filtered(lambda m: m.state == 'draft' and m.move_type in self._PAYMENT_PLAN_MOVE_TYPES and m.scope != 'per_lines'):
                if move._invoice_payment_term_matches_plan_values():
                    continue
                try:
                    move.with_context(skip_auto_generate_payment_term=True).generate_regular_payment_term()
                except UserError:
                    # Keep save non-blocking while users are still editing fields.
                    pass
        return result

    @api.depends("partner_id", "payment_type", "pay_type")
    def _compute_invoice_payment_term_id(self):
        # Keep Odoo's default compute only for custom plans.
        # For fixed/spot we keep whatever is already selected/generated.
        custom_moves = self.filtered(lambda m: m.pay_type == "custom" or m.payment_type == "irregular")
        super(AccountMove, custom_moves)._compute_invoice_payment_term_id()

    @api.onchange('payment_type')
    def _onchange_payment_type_pay_type(self):
        for move in self:
            move.pay_type = self._PAYMENT_PLAN_TO_PAY_TYPE.get(move.payment_type, move.pay_type)
            if move.pay_type == 'spot':
                move.first_payment_type = 'percent'
                move.first_payment_percentage = 100.0

    @api.onchange('pay_type')
    def _onchange_pay_type_generate_payment_term(self):
        # Spot: full payment as 100% — fields are readonly in the view.
        for move in self:
            if move.pay_type == 'spot':
                move.first_payment_type = 'percent'
                move.first_payment_percentage = 100.0
        # Reuse button logic on pay_type change for already-saved draft invoices.
        # Skip unsaved records to avoid creating orphan payment terms.
        for move in self:
            if move.id and move.state == 'draft' and move.move_type in self._PAYMENT_PLAN_MOVE_TYPES:
                try:
                    move.generate_regular_payment_term()
                except UserError:
                    pass

    def _build_fixed_first_payment_lines(self, pay_type):
        """Return safe line_ids commands for first_payment_type='fixed' edge cases."""
        self.ensure_one()
        if self.first_payment_type != 'fixed' or self.first_payment_percentage <= 0:
            return []
        # For non-fixed plans (or fixed with no installments), enforce Odoo constraint:
        # at least one percent line summing to 100.
        if pay_type != 'fixed' or self.installment_count < 1:
            return [
                (0, 0, {
                    'value': 'fixed',
                    'value_amount': self.first_payment_percentage,
                    'nb_days': 0,
                    'delay_type': 'days_after',
                }),
                (0, 0, {
                    'value': 'percent',
                    'value_amount': 100.0,
                    'nb_days': 0,
                    'delay_type': 'days_after',
                }),
            ]
        return []

    def _invoice_payment_term_matches_plan_values(self):
        """Return True when the linked payment term already matches header plan fields."""
        self.ensure_one()
        term = self.invoice_payment_term_id
        if not term or not term.is_installment_term:
            return False

        pay_type = self.pay_type or self._PAYMENT_PLAN_TO_PAY_TYPE.get(self.payment_type)
        if term.pay_type != pay_type:
            return False

        if pay_type == 'custom':
            return bool(term.line_ids)

        if pay_type == 'spot':
            return (
                (term.settlement_trigger or 'cia') == (self.settlement_trigger or 'cia')
                and (term.baseline_date or 'invoice_date') == (self.baseline_date or 'invoice_date')
                and term.first_payment_type == (self.first_payment_type or 'percent')
                and float_compare(
                    term.first_payment_percentage or 0.0,
                    self.first_payment_percentage or 100.0,
                    precision_digits=2,
                ) == 0
            )

        if pay_type == 'fixed':
            return (
                term.installment_count == (self.installment_count or 0)
                and term.first_payment_type == (self.first_payment_type or 'fixed')
                and float_compare(
                    term.first_payment_percentage or 0.0,
                    self.first_payment_percentage or 0.0,
                    precision_digits=2,
                ) == 0
                and (term.installment_frequency or 'monthly') == (self.installment_frequency or 'monthly')
                and (term.baseline_date or 'invoice_date') == (self.baseline_date or 'invoice_date')
                and (term.settlement_trigger or 'cia') == (self.settlement_trigger or 'cia')
            )

        return False

    def generate_regular_payment_term(self):
        """Create an account.payment.term from regular-installment fields and assign it."""
        self.ensure_one()
        if self._invoice_payment_term_matches_plan_values():
            return {'type': 'ir.actions.client', 'tag': 'reload'}
        if self.state != 'draft':
            raise UserError(_("You can generate a payment term only while the document is in draft."))
        if not self.pay_type:
            raise UserError(_("Select a Payment Plan first."))
        if self.pay_type == 'fixed' and (not self.installment_count or self.installment_count < 1):
            raise UserError(_("Set a positive number of installments for Fixed (Auto)."))
        if self.first_payment_type == 'percent' and not (0 <= self.first_payment_percentage <= 100):
            raise UserError(_("First Payment (%) must be between 0 and 100."))

        PaymentTerm = self.env['account.payment.term']
        selected_pay_type = self.pay_type or self._PAYMENT_PLAN_TO_PAY_TYPE.get(self.payment_type) or 'fixed'

        # Spot plans: reuse/create payment term by naming convention
        # for CIA/COD/CBD based on payment-term generated name.
        if selected_pay_type == 'spot':
            spot_vals = {
                'company_id': self.company_id.id,
                'is_installment_term': True,
                'pay_type': 'spot',
                'scope': self.scope or 'per_lines',
                'settlement_trigger': self.settlement_trigger or 'cia',
                'baseline_date': self.baseline_date or 'invoice_date',
                'first_payment_type': self.first_payment_type,
                'first_payment_percentage': self.first_payment_percentage,
            }
            fixed_first_lines = self._build_fixed_first_payment_lines('spot')
            if fixed_first_lines:
                spot_vals['line_ids'] = fixed_first_lines
            # Build name from payment term naming logic (no hardcoded names).
            spot_preview = PaymentTerm.new(spot_vals)
            target_name = spot_preview._generate_auto_name()
            target_name = target_name or _("Installments - %s") % (self.name or self.ref or _("Draft Invoice"))
            # Always create from invoice values so account.payment.term.create()
            # override is executed every time from this action.
            spot_vals['name'] = target_name
            term = PaymentTerm.create(spot_vals)
            self.with_context(skip_auto_generate_payment_term=True).write({'invoice_payment_term_id': term.id})
            return {'type': 'ir.actions.client', 'tag': 'reload'}

        pt_vals = {
            'company_id': self.company_id.id,
            'is_installment_term': True,
            'installment_count': self.installment_count,
            'first_payment_type': self.first_payment_type,
            'first_payment_percentage': self.first_payment_percentage,
            'baseline_date': self.baseline_date,
            'pay_type': selected_pay_type,
            'scope': self.scope or 'per_lines',
            'settlement_trigger': self.settlement_trigger,
        }
        fixed_first_lines = self._build_fixed_first_payment_lines(selected_pay_type)
        if fixed_first_lines:
            pt_vals['line_ids'] = fixed_first_lines
        # For regular plans, keep monthly as default frequency when generating a fixed plan.
        if selected_pay_type == 'fixed':
            pt_vals['installment_frequency'] = self.installment_frequency or 'monthly'
        # account.payment.term.name is required at create-time.
        # Build a name from installment settings before creating the record.
        term_preview = PaymentTerm.new(pt_vals)
        preview_name = term_preview._generate_auto_name()
        pt_vals['name'] = preview_name or _("Installments - %s") % (self.name or self.ref or _("Draft Invoice"))
        term = PaymentTerm.create(pt_vals)
        self.with_context(skip_auto_generate_payment_term=True).write({'invoice_payment_term_id': term.id})
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_post(self):
        # Ensure payment term is generated/updated when confirming (posting).
        for move in self.filtered(lambda m: m.state == 'draft' and m.move_type in self._PAYMENT_PLAN_MOVE_TYPES and m.scope != 'per_lines'):
            if not move._invoice_payment_term_matches_plan_values():
                move.with_context(skip_auto_generate_payment_term=True).generate_regular_payment_term()
        return super().action_post()
    def action_open_invoice_payment_term(self):
        """Open payment term form (lines / preview) when plan is irregular (custom installments)."""
        self.ensure_one()
        if self.pay_type != "custom":
            return False
        if self.invoice_payment_term_id:
            action = self.invoice_payment_term_id.get_formview_action()
            action["target"] = "new"
            return action
        return {
            "type": "ir.actions.act_window",
            "name": _("Payment Terms"),
            "res_model": "account.payment.term",
            "view_mode": "form",
            "target": "new",
            "context": {"default_company_id": self.company_id.id},
        }