# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleSubscriptionPeriod(models.Model):
    _name = 'sale.subscription.period'
    _description = 'Subscription Billing Period'
    _order = 'interval_unit, interval_number'

    name = fields.Char(string='Name', required=True)
    interval_number = fields.Integer(string='Every', required=True, default=1)
    interval_unit = fields.Selection(
        [('days', 'Days'), ('weeks', 'Weeks'), ('months', 'Months'), ('years', 'Years')],
        string='Unit', required=True, default='months',
    )
    active = fields.Boolean(default=True)

    @api.constrains('interval_number')
    def _check_interval_number(self):
        for rec in self:
            if rec.interval_number <= 0:
                raise ValidationError(_("Billing interval must be a positive number."))

    def _get_next_date(self, from_date):
        """Return the next billing date after ``from_date`` for this period.

        Uses dateutil.relativedelta so month/year math is correct (no fractional
        days), unlike a fixed timedelta approximation.
        """
        self.ensure_one()
        if not from_date:
            return False
        n = self.interval_number
        unit = self.interval_unit
        delta = {
            'days': relativedelta(days=n),
            'weeks': relativedelta(weeks=n),
            'months': relativedelta(months=n),
            'years': relativedelta(years=n),
        }.get(unit)
        return from_date + delta if delta else from_date
