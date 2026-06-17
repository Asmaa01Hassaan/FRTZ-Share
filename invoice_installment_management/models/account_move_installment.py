# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountMoveInstallment(models.Model):
    _name = 'account.move.installment'
    _description = 'Invoice Installment'
    _order = 'sequence, date_due'

    name = fields.Char(string='Installment Number', required=True, default='/')
    sequence = fields.Integer(string='Sequence', default=1, required=True)
    move_id = fields.Many2one('account.move', string='Invoice', required=True, ondelete='cascade', index=True)
    partner_id = fields.Many2one('res.partner', string='Partner', related='move_id.partner_id', store=True, readonly=True)
    company_id = fields.Many2one('res.company', string='Company', related='move_id.company_id', store=True, readonly=True)
    
    # Amount fields
    amount_total = fields.Monetary(
        string='Due Amount',
        currency_field='currency_id',
        required=True,
        help='Total amount for this installment'
    )
    currency_id = fields.Many2one('res.currency', string='Currency', related='move_id.currency_id', store=True, readonly=True)
    
    # Date fields
    date_due = fields.Date(string='Due Date', required=True, index=True)
    date_invoice = fields.Date(string='Invoice Date', related='move_id.invoice_date', store=True, readonly=True)
    
    # Payment status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('due', 'Due'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('overdue', 'Overdue'),
    ], string='Status', default='draft', compute='_compute_state', store=True)

    # Stored payment tracking (updated by action_pay_installments or manual actions)
    amount_paid = fields.Monetary(
        string='Amount Paid',
        currency_field='currency_id',
        default=0.0,
        help='Amount already paid for this installment (tracked per installment)',
    )
    amount_residual = fields.Monetary(
        string='Remaining amount',
        currency_field='currency_id',
        compute='_compute_amount_residual',
        store=True,
        help='Remaining amount to be paid',
    )
    paid_date = fields.Date(
        string='Paid Date',
        help='Date of last payment applied to this installment',
    )
    payment_reference = fields.Char(
        string='Payment Reference',
        help='Reference to the payment(s) that paid this installment',
    )
    
    # Payment term line reference
    payment_term_line_id = fields.Many2one(
        'account.payment.term.line',
        string='Payment Term Line',
        help='Reference to the payment term line this installment is based on'
    )
    
    # Invoice line reference (for per-line payment terms)
    invoice_line_id = fields.Many2one(
        'account.move.line',
        string='Invoice Line',
        ondelete='cascade',
        help='Invoice line this installment belongs to (only when payment term is applied per line)'
    )

    # Product related to the invoice line (for display)
    product_id = fields.Many2one(
        related='invoice_line_id.product_id',
        comodel_name='product.product',
        string='Product',
        store=True,
        readonly=True
    )
    
    # Notes
    notes = fields.Text(string='Notes')
    
    @api.depends('amount_total', 'amount_paid', 'date_due')
    def _compute_state(self):
        today = fields.Date.today()
        for installment in self:
            if installment.amount_residual <= 0:
                installment.state = 'paid'
            elif installment.amount_paid > 0:
                installment.state = 'partial'
            elif installment.date_due < today:
                installment.state = 'overdue'
            elif installment.date_due >= today:
                installment.state = 'due'
            else:
                installment.state = 'draft'
    
    @api.depends('amount_total', 'amount_paid')
    def _compute_amount_residual(self):
        """Remaining amount = total - paid (payment is tracked per installment)."""
        for installment in self:
            installment.amount_residual = installment.amount_total - (installment.amount_paid or 0.0)
    
    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            # Try to get sequence, if not exists, use simple numbering
            sequence = self.env['ir.sequence'].sudo().search([('code', '=', 'account.move.installment')], limit=1)
            if sequence:
                vals['name'] = self.env['ir.sequence'].next_by_code('account.move.installment') or '/'
            else:
                # Fallback: use move_id and sequence if available
                if vals.get('move_id') and vals.get('sequence'):
                    move = self.env['account.move'].browse(vals['move_id'])
                    vals['name'] = f"{move.name or 'INV'}-INST-{vals['sequence']}"
                else:
                    vals['name'] = f"INST-{self.env['ir.sequence'].next_by_code('ir.sequence') or '001'}"
        return super().create(vals)
    
    def name_get(self):
        result = []
        for installment in self:
            # Include product name if available
            product_part = f" [{installment.product_id.display_name}]" if installment.product_id else ""
            name = f"{installment.name}{product_part} - {installment.amount_total} {installment.currency_id.symbol} - {installment.date_due}"
            result.append((installment.id, name))
        return result

