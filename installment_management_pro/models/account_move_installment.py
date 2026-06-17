# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountMoveInstallment(models.Model):
    _inherit = 'account.move.installment'

    # ── Reference ──────────────────────────────────────────────
    display_reference = fields.Char(
        string='Reference',
        compute='_compute_display_reference',
        store=True,
        help='Invoice number - Product name',
    )

    # ── Overdue tracking ──────────────────────────────────────
    is_overdue = fields.Boolean(
        string='Is Overdue',
        compute='_compute_overdue_fields',
        store=True,
        index=True,
    )
    days_overdue = fields.Integer(
        string='Days Overdue',
        compute='_compute_overdue_fields',
        store=True,
    )

    # ── Reschedule tracking ───────────────────────────────────
    original_date_due = fields.Date(
        string='Original Due Date',
        readonly=True,
        copy=False,
        help='Due date when installment was first created',
    )
    original_amount = fields.Monetary(
        string='Original Amount',
        currency_field='currency_id',
        readonly=True,
        copy=False,
        help='Amount when installment was first created',
    )
    is_rescheduled = fields.Boolean(
        string='Rescheduled',
        default=False,
        readonly=True,
        copy=False,
    )
    reschedule_count = fields.Integer(
        string='Reschedule Count',
        default=0,
        readonly=True,
        copy=False,
    )

    # ── Related logs ──────────────────────────────────────────
    payment_log_ids = fields.One2many(
        'account.installment.payment.log',
        'installment_id',
        string='Payment History',
    )
    reschedule_log_ids = fields.One2many(
        'account.installment.reschedule.log',
        'installment_id',
        string='Reschedule History',
    )
    payment_log_count = fields.Integer(
        compute='_compute_log_counts',
    )
    reschedule_log_count = fields.Integer(
        compute='_compute_log_counts',
    )

    # ── Computed ──────────────────────────────────────────────

    @api.depends(
        'move_id.name', 'move_id.apply_payment_term_per_line',
        'move_id.invoice_line_ids.product_id',
        'product_id.display_name', 'sequence',
    )
    def _compute_display_reference(self):
        for inst in self:
            parts = []
            if inst.move_id and inst.move_id.name and inst.move_id.name != '/':
                parts.append(inst.move_id.name)

            if inst.move_id and inst.move_id.apply_payment_term_per_line:
                # Per-line: product from linked invoice_line_id
                if inst.product_id:
                    parts.append(f'{inst.product_id.display_name}#{inst.sequence}')
            else:
                # Per-invoice: invoice name + #inst + sequence
                if inst.move_id and parts:
                    parts[-1] = f'{parts[-1]}#inst{inst.sequence}'

            inst.display_reference = ' - '.join(parts) if parts else (inst.name or '/')

    @api.depends('date_due', 'state')
    def _compute_overdue_fields(self):
        today = fields.Date.today()
        for inst in self:
            if (inst.state in ('draft', 'due', 'partial', 'overdue')
                    and inst.date_due and inst.date_due < today
                    and inst.amount_residual > 0):
                inst.is_overdue = True
                inst.days_overdue = (today - inst.date_due).days
            else:
                inst.is_overdue = False
                inst.days_overdue = 0

    def _compute_log_counts(self):
        for inst in self:
            inst.payment_log_count = len(inst.payment_log_ids)
            inst.reschedule_log_count = len(inst.reschedule_log_ids)

    # ── Constraints ───────────────────────────────────────────

    @api.constrains('amount_paid', 'amount_total')
    def _check_amount_paid(self):
        for inst in self:
            if inst.amount_paid and inst.amount_total and inst.amount_paid > inst.amount_total:
                raise ValidationError(
                    _("Paid amount (%(paid)s) cannot exceed installment amount (%(total)s) "
                      "on installment %(name)s.",
                      paid=inst.amount_paid, total=inst.amount_total, name=inst.name)
                )

    # ── Snapshot originals on first create ────────────────────

    @api.model
    def create(self, vals):
        if isinstance(vals, dict):
            vals_list = [vals]
        else:
            vals_list = vals

        for v in vals_list:
            if not v.get('original_date_due') and v.get('date_due'):
                v['original_date_due'] = v['date_due']
            if not v.get('original_amount') and v.get('amount_total'):
                v['original_amount'] = v['amount_total']

        records = super().create(vals if not isinstance(vals, dict) else vals_list[0])
        return records

    # ── Cron: refresh overdue flags ───────────────────────────

    @api.model
    def _cron_update_overdue(self):
        """Called daily by cron to refresh overdue flags and states."""
        today = fields.Date.today()
        installments = self.search([
            ('state', 'in', ('draft', 'due', 'partial')),
            ('date_due', '<', today),
            ('amount_residual', '>', 0),
        ])
        if not installments:
            return
        installments.modified(['date_due'])
        installments.flush_recordset(['state', 'is_overdue', 'days_overdue'])

    # ── Actions ───────────────────────────────────────────────

    def action_view_payment_logs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payment History'),
            'res_model': 'account.installment.payment.log',
            'view_mode': 'list,form',
            'domain': [('installment_id', '=', self.id)],
            'context': {'default_installment_id': self.id},
        }

    def action_view_reschedule_logs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reschedule History'),
            'res_model': 'account.installment.reschedule.log',
            'view_mode': 'list,form',
            'domain': [('installment_id', '=', self.id)],
        }
