# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class InstallmentScheduleWizard(models.TransientModel):
    _name = 'installment.schedule.wizard'
    _description = 'Schedule / Reschedule Installments by Customer'

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        domain="[('type', '!=', 'private')]",
    )
    line_ids = fields.One2many(
        'installment.schedule.wizard.line',
        'wizard_id',
        string='Installments',
    )
    reason = fields.Text(
        string='Reason for Rescheduling',
    )

    def action_load_installments(self):
        """Button: load customer installments as real DB records."""
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_('Please select a customer first.'))

        self.line_ids.unlink()

        installments = self.env['account.move.installment'].search([
            ('partner_id', 'child_of', self.partner_id.id),
            ('state', 'in', ('draft', 'due', 'overdue')),
            ('amount_residual', '>', 0),
        ], order='date_due asc')

        if not installments:
            raise UserError(_('No unpaid installments found for this customer.'))

        line_vals = []
        for inst in installments:
            line_vals.append({
                'wizard_id': self.id,
                'installment_id': inst.id,
                'current_date_due': inst.date_due,
                'new_date_due': inst.date_due,
            })
        self.env['installment.schedule.wizard.line'].create(line_vals)

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_apply_schedule(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('Please load installments first.'))
        if not self.reason:
            raise UserError(_('Please enter a reason for rescheduling.'))

        selected = self.line_ids.filtered(lambda l: l.selected and l.installment_id)
        if not selected:
            raise UserError(_('Please select at least one installment to reschedule.'))

        missing_date = selected.filtered(lambda l: not l.new_date_due)
        if missing_date:
            raise UserError(_('Please set a New Due Date for all selected installments.'))

        changed = selected.filtered(
            lambda l: l.new_date_due != l.current_date_due
        )
        if not changed:
            raise UserError(_('No date changes detected on selected installments.'))

        log_model = self.env['account.installment.reschedule.log']
        for line in changed:
            inst = line.installment_id
            log_model.create({
                'installment_id': inst.id,
                'change_type': 'date_change',
                'old_date_due': inst.date_due,
                'new_date_due': line.new_date_due,
                'old_amount': inst.amount_total,
                'new_amount': inst.amount_total,
                'reason': self.reason,
            })
            inst.write({
                'date_due': line.new_date_due,
                'is_rescheduled': True,
                'reschedule_count': inst.reschedule_count + 1,
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Rescheduled'),
                'message': _('%d installment(s) rescheduled successfully.') % len(changed),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }


class InstallmentScheduleWizardLine(models.TransientModel):
    _name = 'installment.schedule.wizard.line'
    _description = 'Schedule Wizard Line'

    wizard_id = fields.Many2one(
        'installment.schedule.wizard',
        ondelete='cascade',
    )
    selected = fields.Boolean(string='Select', default=False)
    installment_id = fields.Many2one(
        'account.move.installment',
        string='Installment',
    )
    # Related fields — read from installment_id, always correct
    move_id = fields.Many2one(
        related='installment_id.move_id',
        string='Invoice',
    )
    display_reference = fields.Char(
        related='installment_id.display_reference',
        string='Reference',
    )
    amount_total = fields.Monetary(
        related='installment_id.amount_total',
        string='Amount',
    )
    amount_paid = fields.Monetary(
        related='installment_id.amount_paid',
        string='Paid',
    )
    amount_residual = fields.Monetary(
        related='installment_id.amount_residual',
        string='Remaining',
    )
    state = fields.Selection(
        related='installment_id.state',
        string='Status',
    )
    currency_id = fields.Many2one(
        related='installment_id.currency_id',
    )
    # Editable fields
    current_date_due = fields.Date(string='Current Due Date')
    new_date_due = fields.Date(string='New Due Date')
