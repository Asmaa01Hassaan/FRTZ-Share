# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    show_first_payment_per_lines_mode = fields.Boolean(
        compute='_compute_first_payment_per_lines_values',
    )
    line_first_payment_amount = fields.Monetary(
        string='First Payment Total',
        currency_field='currency_id',
        compute='_compute_first_payment_per_lines_values',
    )
    payment_amount_mode = fields.Selection(
        selection=[
            ('full', _('Full Amount')),
            ('first_payment_per_lines', _('First Payment (Per Lines)')),
        ],
        string='Amount to Pay',
        default='full',
    )

    @api.depends('line_ids', 'line_ids.move_id.apply_payment_term_per_line', 'line_ids.move_id.scope')
    def _compute_first_payment_per_lines_values(self):
        for wizard in self:
            moves = wizard.line_ids.move_id
            show_mode = bool(
                len(moves) == 1
                and moves.is_invoice(include_receipts=True)
                and (
                    moves.apply_payment_term_per_line
                    or getattr(moves, 'scope', False) == 'per_lines'
                )
            )
            wizard.line_first_payment_amount = (
                moves._get_total_line_first_payment_amount() if show_mode else 0.0
            )
            wizard.show_first_payment_per_lines_mode = (
                show_mode and wizard.line_first_payment_amount > 0
            )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        move = self.env['account.move']
        if self.env.context.get('active_model') == 'account.move' and self.env.context.get('active_id'):
            move = self.env['account.move'].browse(self.env.context['active_id']).exists()
        elif res.get('line_ids') and isinstance(res['line_ids'][0], (list, tuple)):
            line_ids = [command[1] for command in res['line_ids'] if command[0] == 4]
            if line_ids:
                lines = self.env['account.move.line'].browse(line_ids)
                if len(lines.move_id) == 1:
                    move = lines.move_id

        if (
            move
            and move.is_invoice(include_receipts=True)
            and (move.apply_payment_term_per_line or getattr(move, 'scope', False) == 'per_lines')
        ):
            first_payment = move._get_total_line_first_payment_amount()
            if first_payment > 0:
                res['payment_amount_mode'] = 'first_payment_per_lines'
                if 'amount' in fields_list:
                    res['amount'] = first_payment
        return res

    @api.depends(
        'can_edit_wizard',
        'source_amount',
        'source_amount_currency',
        'source_currency_id',
        'company_id',
        'currency_id',
        'payment_date',
        'installments_mode',
        'payment_amount_mode',
        'line_first_payment_amount',
        'show_first_payment_per_lines_mode',
    )
    def _compute_amount(self):
        first_payment_wizards = self.filtered(
            lambda wizard: (
                wizard.show_first_payment_per_lines_mode
                and wizard.payment_amount_mode == 'first_payment_per_lines'
                and not wizard.custom_user_amount
            )
        )
        super(AccountPaymentRegister, self - first_payment_wizards)._compute_amount()
        for wizard in first_payment_wizards:
            if (
                wizard.journal_id
                and wizard.currency_id
                and wizard.payment_date
            ):
                wizard.amount = wizard.line_first_payment_amount
            else:
                wizard.amount = wizard.amount

    @api.onchange('payment_amount_mode')
    def _onchange_payment_amount_mode(self):
        self.custom_user_amount = None
        self.custom_user_currency_id = None
        if not self.show_first_payment_per_lines_mode:
            return
        if self.payment_amount_mode == 'first_payment_per_lines':
            self.amount = self.line_first_payment_amount
        elif self.batches:
            self.amount = self._get_total_amounts_to_pay(self.batches)['full_amount']

    @api.onchange('amount')
    def _onchange_amount(self):
        super()._onchange_amount()
        if (
            not self.show_first_payment_per_lines_mode
            or not self.currency_id
            or not self.can_edit_wizard
        ):
            return
        if self.currency_id.is_zero(self.amount - self.line_first_payment_amount):
            self.payment_amount_mode = 'first_payment_per_lines'
        elif self.batches:
            full_amount = self._get_total_amounts_to_pay(self.batches)['full_amount']
            if self.currency_id.is_zero(self.amount - full_amount):
                self.payment_amount_mode = 'full'
