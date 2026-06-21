# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # Drives the hybrid order: each line is independently one-time or recurring.
    subscription_line_type = fields.Selection(
        [('one_time', 'One-time'), ('recurring', 'Recurring')],
        string='Billing Type',
        compute='_compute_subscription_line_type', store=True, readonly=False,
        help="One-time lines are billed once (e.g. setup fee, SIM). "
             "Recurring lines are billed every subscription cycle.",
    )
    # Item-level pause: a paused recurring line is skipped by the billing engine
    # while the rest of the subscription keeps billing normally.
    subscription_line_state = fields.Selection(
        [('active', 'Active'), ('paused', 'Paused')],
        string='Line Status', default='active', copy=False,
    )
    # One-time lines are flagged once billed so they are never billed again.
    subscription_invoiced = fields.Boolean(
        string='One-time Invoiced', default=False, copy=False)

    # --- Item-level pause details (current/last pause) ---
    pause_reason_id = fields.Many2one(
        'subscription.reason', string='Pause Reason', copy=False,
        domain="[('reason_type', '=', 'line_pause')]")
    pause_note = fields.Char(string='Pause Note', copy=False)
    pause_date = fields.Date(string='Paused On', copy=False)
    planned_resume_date = fields.Date(
        string='Planned Resume Date', copy=False,
        help="Optional. A cron auto-resumes the line on this date.")
    charge_suspension_fee = fields.Boolean(
        string='Charge Reduced Fee While Paused', default=False, copy=False,
        help="If set, the paused line is still billed a reduced fee each cycle "
             "instead of being skipped entirely.")
    suspension_fee_amount = fields.Monetary(
        string='Suspension Fee / Cycle', currency_field='currency_id', copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        # super() runs the full create chain (incl. pricelist_expression, which
        # recomputes price from the pricelist); we then re-apply the per-period
        # subscription price so it takes precedence for recurring lines.
        lines = super().create(vals_list)
        lines._apply_subscription_price()
        return lines

    def write(self, vals):
        res = super().write(vals)
        trigger = {'product_id', 'product_uom', 'product_uom_qty', 'subscription_line_type'}
        if trigger & set(vals):
            self._apply_subscription_price()
        return res

    def _apply_subscription_price(self):
        """Force recurring subscription lines onto the product's per-period price.

        Runs after the standard/pricelist pipeline so it has the final say. No-op
        for one-time lines, non-subscription products, orders without a billing
        period, or products that have no price defined for that period.
        """
        for line in self:
            if line.display_type or not line.product_id or not line.order_id:
                continue
            period = line.order_id.subscription_period_id
            if not period or line.subscription_line_type == 'one_time':
                continue
            price = line.product_id.product_tmpl_id._get_subscription_price(period)
            if price is not None and line.price_unit != price:
                line.price_unit = price

    def _get_display_price(self):
        """For recurring subscription lines, use the product's per-period
        subscription price (falls back to the standard price when none is set).

        Overriding _get_display_price (instead of _compute_price_unit) keeps the
        standard pricing pipeline intact - technical_price_unit, tax handling and
        the manual-edit guard all keep working, so price_unit is never left null.
        """
        # Apply the per-period subscription price to any line that has a billing
        # period and isn't explicitly one-time. `_get_subscription_price` returns
        # None for products without a price for that period, so non-recurring
        # products naturally keep their standard price.
        if (not self.display_type and self.product_id
                and self.order_id.subscription_period_id
                and self.subscription_line_type != 'one_time'):
            price = self.product_id.product_tmpl_id._get_subscription_price(
                self.order_id.subscription_period_id)
            if price is not None:
                return price
        return super()._get_display_price()

    @api.depends('product_id', 'product_id.subscription_price_ids', 'display_type')
    def _compute_subscription_line_type(self):
        for line in self:
            if line.display_type:
                line.subscription_line_type = False
            elif line.product_id:
                # A product is recurring when it has per-period subscription
                # prices configured; otherwise it is a one-time line.
                line.subscription_line_type = (
                    'recurring' if line.product_id.subscription_price_ids else 'one_time'
                )
            elif not line.subscription_line_type:
                line.subscription_line_type = 'one_time'

    def action_open_pause_wizard(self):
        """Open the pause wizard (the UI gate that forces a reason)."""
        self.ensure_one()
        if self.subscription_line_type != 'recurring':
            raise UserError(_("Only recurring lines can be paused."))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pause Line'),
            'res_model': 'subscription.line.pause.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_line_id': self.id,
                'default_suspension_fee_amount': self.product_id.suspension_fee,
            },
        }

    def action_pause_subscription_line(self, reason_id=False, note=False,
                                       planned_resume_date=False,
                                       charge_fee=False, fee_amount=False):
        for line in self:
            if line.subscription_line_type != 'recurring':
                raise UserError(_("Only recurring lines can be paused."))
            if line.subscription_line_state == 'paused':
                continue
            line.write({
                'subscription_line_state': 'paused',
                'pause_reason_id': reason_id or False,
                'pause_note': note or False,
                'pause_date': fields.Date.context_today(line),
                'planned_resume_date': planned_resume_date or False,
                'charge_suspension_fee': bool(charge_fee),
                'suspension_fee_amount': fee_amount or 0.0,
            })
            line.order_id._log_state_change('pause_line', reason_id=reason_id, note=note, line=line)
            line.order_id._post_provisioning_signal(
                'pause_line', line=line, reason_id=reason_id, note=note)
        return True

    def action_resume_subscription_line(self):
        for line in self:
            if line.subscription_line_state != 'paused':
                continue
            line.write({
                'subscription_line_state': 'active',
                'pause_reason_id': False,
                'pause_note': False,
                'pause_date': False,
                'planned_resume_date': False,
                'charge_suspension_fee': False,
                'suspension_fee_amount': 0.0,
            })
            line.order_id._log_state_change('resume_line', line=line)
            line.order_id._post_provisioning_signal('resume_line', line=line)
        return True

    @api.model
    def _cron_auto_resume_paused_lines(self):
        today = fields.Date.context_today(self)
        lines = self.search([
            ('subscription_line_state', '=', 'paused'),
            ('planned_resume_date', '!=', False),
            ('planned_resume_date', '<=', today),
        ])
        if lines:
            lines.action_resume_subscription_line()
        return True
