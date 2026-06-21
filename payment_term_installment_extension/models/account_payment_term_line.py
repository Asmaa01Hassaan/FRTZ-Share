# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class AccountPaymentTermLine(models.Model):
    _inherit = 'account.payment.term.line'
    
    method = fields.Selection([
        ('sd', 'SD-Salary deduction'),
        ('sdd', 'SDD-Salary Deduction Duble'),
    ], string="Method", default='sd',
        help="Payment method for this line")
    
    date_calculation_type = fields.Selection([
        ('days', 'Number of Days'),
        ('fixed_date', 'Fixed Date'),
    ], string="Date Calculation Type", default='days',
        help="Choose how to calculate the due date: using number of days or a fixed date")
    
    fixed_due_date = fields.Date(
        string="Fixed Due Date",
        help="Specific due date for this payment term line (used when Date Calculation Type is 'Fixed Date')"
    )
    
    def _get_due_date(self, date_ref):
        """
        Override to support both nb_days calculation and fixed_due_date.
        If date_calculation_type is 'fixed_date', return fixed_due_date.
        Otherwise, use the standard nb_days calculation.
        """
        if self.date_calculation_type == 'fixed_date' and self.fixed_due_date:
            return self.fixed_due_date
        # Use standard Odoo calculation for nb_days
        return super()._get_due_date(date_ref)
    
    @api.constrains('date_calculation_type', 'fixed_due_date', 'nb_days')
    def _check_date_calculation(self):
        """
        Ensure that when date_calculation_type is 'fixed_date', fixed_due_date is set.
        When date_calculation_type is 'days', nb_days should be set (standard Odoo validation).
        """
        for line in self:
            if line.date_calculation_type == 'fixed_date' and not line.fixed_due_date:
                raise models.ValidationError(
                    _("Fixed Due Date is required when Date Calculation Type is 'Fixed Date'.")
                )
















