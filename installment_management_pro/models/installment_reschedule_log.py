# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AccountInstallmentRescheduleLog(models.Model):
    _name = 'account.installment.reschedule.log'
    _description = 'Installment Reschedule Log'
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference',
        readonly=True,
        copy=False,
        default='New',
    )
    installment_id = fields.Many2one(
        'account.move.installment',
        string='Installment',
        required=True,
        ondelete='cascade',
        index=True,
    )
    move_id = fields.Many2one(
        'account.move',
        string='Invoice',
        related='installment_id.move_id',
        store=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        related='installment_id.partner_id',
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='installment_id.currency_id',
        store=True,
        readonly=True,
    )
    display_reference = fields.Char(
        string='Installment Ref.',
        related='installment_id.display_reference',
        store=True,
        readonly=True,
    )
    user_id = fields.Many2one(
        'res.users',
        string='Rescheduled By',
        default=lambda self: self.env.user,
        readonly=True,
    )

    # ── Change details ────────────────────────────────────────
    change_type = fields.Selection(
        [
            ('date_change', 'Date Change'),
            ('amount_change', 'Amount Change'),
            ('split', 'Split'),
            ('merge', 'Merge'),
            ('cancel', 'Cancellation'),
        ],
        string='Change Type',
        required=True,
    )
    old_date_due = fields.Date(string='Old Due Date', readonly=True)
    new_date_due = fields.Date(string='New Due Date', readonly=True)
    old_amount = fields.Monetary(
        string='Old Amount',
        currency_field='currency_id',
        readonly=True,
    )
    new_amount = fields.Monetary(
        string='New Amount',
        currency_field='currency_id',
        readonly=True,
    )
    reason = fields.Text(string='Reason')

    @api.model
    def create(self, vals):
        if isinstance(vals, dict):
            vals_list = [vals]
        else:
            vals_list = vals
        for v in vals_list:
            if v.get('name', 'New') == 'New':
                v['name'] = self.env['ir.sequence'].next_by_code(
                    'account.installment.reschedule.log'
                ) or 'New'
        return super().create(vals if not isinstance(vals, dict) else vals_list[0])
