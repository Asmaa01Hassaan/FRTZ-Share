# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class InstallmentRescheduleWizard(models.TransientModel):
    _name = 'installment.reschedule.wizard'
    _description = 'Reschedule Installments Wizard'

    move_id = fields.Many2one(
        'account.move',
        string='Invoice',
        required=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='move_id.currency_id',
        readonly=True,
    )
    line_ids = fields.One2many(
        'installment.reschedule.wizard.line',
        'wizard_id',
        string='Installments',
    )
    reason = fields.Text(
        string='Reason for Rescheduling',
        required=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ctx = self.env.context
        active_ids = ctx.get('active_installment_ids', [])
        move_id = res.get('move_id') or ctx.get('default_move_id')
        if move_id and not active_ids:
            move = self.env['account.move'].browse(move_id)
            active_ids = move.installment_ids.filtered(
                lambda i: i.state in ('draft', 'due', 'partial', 'overdue')
                and i.amount_residual > 0
            ).ids

        if active_ids:
            installments = self.env['account.move.installment'].browse(active_ids)
            lines = []
            for inst in installments:
                lines.append((0, 0, {
                    'installment_id': inst.id,
                    'current_date_due': inst.date_due,
                    'new_date_due': inst.date_due,
                    'current_amount': inst.amount_total,
                    'new_amount': inst.amount_total,
                    'amount_paid': inst.amount_paid,
                    'amount_residual': inst.amount_residual,
                }))
            res['line_ids'] = lines
        return res

    def action_apply_reschedule(self):
        """Apply the rescheduling changes and log history."""
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('No installments to reschedule.'))

        changed = self.line_ids.filtered(
            lambda l: l.new_date_due != l.current_date_due
            or l.new_amount != l.current_amount
        )
        if not changed:
            raise UserError(_('No changes detected. Please modify at least one date or amount.'))

        total_original = sum(self.line_ids.mapped('current_amount'))
        total_new = sum(self.line_ids.mapped('new_amount'))
        rounding = self.currency_id.rounding or 0.01
        if abs(total_original - total_new) > rounding:
            raise ValidationError(
                _("Total amounts don't match. Original total: %(orig)s, "
                  "New total: %(new)s. Difference: %(diff)s",
                  orig=total_original, new=total_new,
                  diff=abs(total_original - total_new))
            )

        log_model = self.env['account.installment.reschedule.log']
        for line in changed:
            inst = line.installment_id
            change_types = []
            if line.new_date_due != line.current_date_due:
                change_types.append('date_change')
            if line.new_amount != line.current_amount:
                change_types.append('amount_change')

            for ct in change_types:
                log_model.create({
                    'installment_id': inst.id,
                    'change_type': ct,
                    'old_date_due': inst.date_due,
                    'new_date_due': line.new_date_due,
                    'old_amount': inst.amount_total,
                    'new_amount': line.new_amount,
                    'reason': self.reason,
                })

            vals = {}
            if line.new_date_due != line.current_date_due:
                vals['date_due'] = line.new_date_due
            if line.new_amount != line.current_amount:
                vals['amount_total'] = line.new_amount
            vals['is_rescheduled'] = True
            vals['reschedule_count'] = inst.reschedule_count + 1
            inst.write(vals)

        return {'type': 'ir.actions.act_window_close'}


class InstallmentRescheduleWizardLine(models.TransientModel):
    _name = 'installment.reschedule.wizard.line'
    _description = 'Reschedule Wizard Line'

    wizard_id = fields.Many2one(
        'installment.reschedule.wizard',
        string='Wizard',
        ondelete='cascade',
    )
    installment_id = fields.Many2one(
        'account.move.installment',
        string='Installment',
        required=True,
        readonly=True,
    )
    display_reference = fields.Char(
        related='installment_id.display_reference',
        string='Reference',
        readonly=True,
    )
    current_date_due = fields.Date(
        string='Current Due Date',
        readonly=True,
    )
    new_date_due = fields.Date(
        string='New Due Date',
        required=True,
    )
    current_amount = fields.Monetary(
        string='Current Amount',
        currency_field='currency_id',
        readonly=True,
    )
    new_amount = fields.Monetary(
        string='New Amount',
        currency_field='currency_id',
        required=True,
    )
    amount_paid = fields.Monetary(
        string='Amount Paid',
        currency_field='currency_id',
        readonly=True,
    )
    amount_residual = fields.Monetary(
        string='Remaining',
        currency_field='currency_id',
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='installment_id.currency_id',
        readonly=True,
    )

    @api.constrains('new_amount', 'amount_paid')
    def _check_new_amount(self):
        for line in self:
            if line.new_amount < line.amount_paid:
                raise ValidationError(
                    _("New amount (%(new)s) cannot be less than already paid amount (%(paid)s).",
                      new=line.new_amount, paid=line.amount_paid)
                )
