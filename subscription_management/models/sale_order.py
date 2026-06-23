# -*- coding: utf-8 -*-
import logging
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import format_date

_logger = logging.getLogger(__name__)

# Safety cap on how many missed cycles a single cron run will catch up per order.
CATCH_UP_LIMIT = 36


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # ------------------------------------------------------------------
    # Freeze the whole form when a subscription is terminated
    # ------------------------------------------------------------------
    # Expression injected as a readonly modifier on every sheet field so a
    # cancelled/closed subscription is fully read-only in the UI. Parent-node
    # readonly does NOT cascade to children in the Odoo 18 web client, so we set
    # it per field (server-side) instead of once on the <sheet>.
    _SUBSCRIPTION_FREEZE_EXPR = (
        "is_subscription and subscription_state in ('cancelled', 'closed')")

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        if view_type == 'form':
            res['arch'] = self._subscription_freeze_form_arch(res['arch'])
        return res

    @api.model
    def _subscription_freeze_form_arch(self, arch):
        """Add the freeze readonly modifier to every editable field of the main
        sale order form (so a terminated subscription cannot be edited). Only
        forms that expose both subscription driver fields are touched, and fields
        inside embedded o2m/m2m sub-views are left alone (their context has no
        subscription_state)."""
        from lxml import etree
        try:
            doc = etree.fromstring(arch)
        except Exception:  # noqa: BLE001 - never break view loading on parse issues
            return arch
        names = {f.get('name') for f in doc.xpath('//field')}
        if not {'is_subscription', 'subscription_state'} <= names:
            return arch  # not the subscription-aware form; leave untouched
        freeze = self._SUBSCRIPTION_FREEZE_EXPR
        for sheet in doc.xpath('//sheet'):
            for field in sheet.xpath('.//field'):
                # Only freeze top-level order fields. Skip any field nested inside
                # another field, i.e. a column/field of an embedded o2m/m2m
                # sub-view (list, kanban OR form). Those records have no
                # is_subscription/subscription_state in their own context, so the
                # injected modifier would crash with "is_subscription is not defined".
                if field.xpath('ancestor::field'):
                    continue
                existing = (field.get('readonly') or '').strip()
                if existing in ('1', 'True', 'true'):
                    continue  # already always read-only
                if existing:
                    field.set('readonly', '(%s) or (%s)' % (existing, freeze))
                else:
                    field.set('readonly', freeze)
        return etree.tostring(doc, encoding='unicode')

    is_subscription = fields.Boolean(
        string='Is a Subscription',
        compute='_compute_is_subscription', store=True, readonly=True,
        help="Driven by the Sale Order Type: True when the chosen order type is "
             "classified as 'Subscription'. This is what switches the order onto "
             "the subscription_management engine.")
    subscription_state = fields.Selection(
        [
            ('pending', 'Pending'),
            ('active', 'Active'),
            ('suspended', 'Suspended'),
            ('cancelled', 'Cancelled'),
            ('closed', 'Closed'),
        ],
        string='Subscription Status', default='pending', copy=False, tracking=True,
    )
    subscription_period_id = fields.Many2one(
        'sale.subscription.period', string='Billing Period', copy=True)
    subscription_start_date = fields.Date(string='Start Date', copy=False)
    subscription_next_invoice_date = fields.Date(
        string='Next Invoice Date', copy=False, tracking=True)
    subscription_end_date = fields.Date(
        string='End Date',
        help="Optional. Once the next invoice date passes this date, the "
             "subscription is closed and no new invoices are generated.")
    subscription_charge_ids = fields.One2many(
        'sale.subscription.charge', 'order_id', string='Ad-hoc Charges', copy=False)

    subscription_recurring_count = fields.Integer(
        compute='_compute_subscription_counts', string='Recurring Lines')
    subscription_pending_charge_count = fields.Integer(
        compute='_compute_subscription_counts', string='Pending Charges')
    subscription_invoice_ids = fields.One2many(
        'account.move', 'subscription_order_id', string='Subscription Invoices', copy=False)
    subscription_invoice_count = fields.Integer(
        compute='_compute_subscription_invoice_count', string='Invoices')

    # --- Suspension (temporary) / Cancellation (permanent) with reason ---
    suspension_reason_id = fields.Many2one(
        'subscription.reason', string='Suspension Reason', copy=False, tracking=True,
        domain="[('reason_type', '=', 'suspension')]")
    suspension_note = fields.Text(string='Suspension Note', copy=False)
    suspended_on = fields.Datetime(string='Suspended On', copy=False, readonly=True)
    suspended_by_id = fields.Many2one('res.users', string='Suspended By', copy=False, readonly=True)
    cancellation_reason_id = fields.Many2one(
        'subscription.reason', string='Cancellation Reason', copy=False, tracking=True,
        domain="[('reason_type', '=', 'cancellation')]")
    cancellation_note = fields.Text(string='Cancellation Note', copy=False)
    cancelled_on = fields.Datetime(string='Cancelled On', copy=False, readonly=True)
    cancelled_by_id = fields.Many2one('res.users', string='Cancelled By', copy=False, readonly=True)
    subscription_log_ids = fields.One2many(
        'subscription.state.log', 'order_id', string='State History', copy=False)

    # --- Tracking: recurring amount + monthly normalised MRR + overdue flag ---
    subscription_recurring_amount = fields.Monetary(
        compute='_compute_subscription_recurring_amount', string='Recurring Amount',
        currency_field='currency_id',
        help="Per-cycle recurring amount: sum of the active recurring lines.")
    subscription_mrr = fields.Monetary(
        compute='_compute_subscription_recurring_amount', string='MRR',
        currency_field='currency_id',
        help="Recurring amount normalised to a monthly figure for revenue tracking.")
    subscription_is_overdue = fields.Boolean(
        compute='_compute_subscription_is_overdue',
        search='_search_subscription_is_overdue', string='Overdue')

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends('sale_order_type_id.order_classification')
    def _compute_is_subscription(self):
        """Subscription orders are driven by the Sale Order Type classification."""
        for order in self:
            order.is_subscription = (
                order.sale_order_type_id.order_classification == 'subscription'
            )

    @api.depends('order_line.subscription_line_type', 'subscription_charge_ids.state')
    def _compute_subscription_counts(self):
        for order in self:
            order.subscription_recurring_count = len(order.order_line.filtered(
                lambda l: not l.display_type and l.subscription_line_type == 'recurring'))
            order.subscription_pending_charge_count = len(
                order.subscription_charge_ids.filtered(lambda c: c.state == 'pending'))

    @api.depends('subscription_invoice_ids')
    def _compute_subscription_invoice_count(self):
        for order in self:
            order.subscription_invoice_count = len(order.subscription_invoice_ids)

    @api.depends('order_line.price_subtotal', 'order_line.subscription_line_type',
                 'order_line.subscription_line_state', 'subscription_period_id')
    def _compute_subscription_recurring_amount(self):
        for order in self:
            recurring = order.order_line.filtered(
                lambda l: not l.display_type
                and l.subscription_line_type == 'recurring'
                and l.subscription_line_state == 'active')
            amount = sum(recurring.mapped('price_subtotal'))
            order.subscription_recurring_amount = amount
            order.subscription_mrr = order._normalise_to_monthly(amount)

    def _normalise_to_monthly(self, amount):
        """Convert a per-cycle amount into a comparable monthly figure."""
        self.ensure_one()
        period = self.subscription_period_id
        if not period or not period.interval_number:
            return amount
        n = period.interval_number
        factor = {
            'days': 30.0 / n,
            'weeks': 52.0 / (12.0 * n),
            'months': 1.0 / n,
            'years': 1.0 / (12.0 * n),
        }.get(period.interval_unit, 1.0)
        return amount * factor

    def _compute_subscription_is_overdue(self):
        today = fields.Date.context_today(self)
        for order in self:
            order.subscription_is_overdue = bool(
                order.subscription_state == 'active'
                and order.subscription_next_invoice_date
                and order.subscription_next_invoice_date < today)

    def _search_subscription_is_overdue(self, operator, value):
        today = fields.Date.context_today(self)
        overdue = [
            ('subscription_state', '=', 'active'),
            ('subscription_next_invoice_date', '!=', False),
            ('subscription_next_invoice_date', '<', today),
        ]
        want_overdue = (operator == '=' and value) or (operator == '!=' and not value)
        if want_overdue:
            return overdue
        # negation: not active, OR no next date, OR next date today/future
        return [
            '|', ('subscription_state', '!=', 'active'),
            '|', ('subscription_next_invoice_date', '=', False),
            ('subscription_next_invoice_date', '>=', today),
        ]

    @api.onchange('subscription_period_id')
    def _onchange_subscription_period_id(self):
        """Re-price recurring lines from the product's price for the new period."""
        recurring = self.order_line.filtered(
            lambda l: not l.display_type and l.subscription_line_type == 'recurring')
        if recurring:
            recurring.with_context(force_price_recomputation=True)._compute_price_unit()

    # ------------------------------------------------------------------
    # Lifecycle transitions (order level)
    # ------------------------------------------------------------------
    def _check_is_subscription(self):
        for order in self:
            if not order.is_subscription:
                raise UserError(_("This action is only available on subscription orders."))

    def action_activate_subscription(self):
        self._check_is_subscription()
        today = fields.Date.context_today(self)
        for order in self:
            if order.subscription_state in ('cancelled', 'closed'):
                raise UserError(_("A cancelled or closed subscription cannot be re-activated."))
            if not order.subscription_period_id:
                raise UserError(_("Set a Billing Period before activating the subscription."))
            # Subscriptions skip the separate Confirm step: confirm the quotation
            # here (if still a draft/sent quotation), then activate.
            if order.state in ('draft', 'sent'):
                order.action_confirm()
            if order.state != 'sale':
                raise UserError(_("The order must be confirmed to activate the subscription."))
            vals = {'subscription_state': 'active'}
            start = order.subscription_start_date or today
            vals['subscription_start_date'] = start
            if not order.subscription_next_invoice_date:
                vals['subscription_next_invoice_date'] = start
            order.write(vals)
            order._log_state_change('activate')
            order._post_provisioning_signal('activate')
        return True

    # Technical (chatter / activity) fields that may still change once a
    # subscription is terminated; every other field is frozen. See write().
    _SUBSCRIPTION_TERMINATED_ALLOWED_FIELDS = frozenset({
        'message_follower_ids', 'message_partner_ids', 'message_ids',
        'message_main_attachment_id', 'message_attachment_count',
        'message_has_error', 'message_has_error_counter', 'message_has_sms_error',
        'message_needaction', 'message_needaction_counter',
        'message_unread', 'message_unread_counter', 'website_message_ids',
        'activity_ids', 'activity_state', 'activity_user_id', 'activity_type_id',
        'activity_type_icon', 'activity_date_deadline', 'my_activity_date_deadline',
        'activity_summary', 'activity_exception_decoration',
        'activity_exception_icon', 'activity_calendar_event_id',
    })

    def write(self, vals):
        """Freeze terminated subscriptions: once a subscription order is
        cancelled/closed it can no longer be edited (only chatter/activity
        technical fields may change). The termination flow itself bypasses this
        via the 'subscription_lifecycle_write' context."""
        if not self.env.context.get('subscription_lifecycle_write'):
            frozen = self.filtered(
                lambda o: o.is_subscription
                and o.subscription_state in ('cancelled', 'closed'))
            if frozen and not set(vals).issubset(
                    self._SUBSCRIPTION_TERMINATED_ALLOWED_FIELDS):
                raise UserError(_(
                    "This subscription is terminated and can no longer be "
                    "modified."))
        return super().write(vals)

    def action_suspend_subscription(self, reason_id=False, note=False):
        """Temporary full suspension. reason_id/note are required by the UI wizard;
        kept optional here so automation can call it too."""
        self._check_is_subscription()
        for order in self:
            if order.subscription_state != 'active':
                raise UserError(_("Only active subscriptions can be suspended."))
            order.write({
                'subscription_state': 'suspended',
                'suspension_reason_id': reason_id or False,
                'suspension_note': note or False,
                'suspended_on': fields.Datetime.now(),
                'suspended_by_id': self.env.uid,
            })
            order._log_state_change('suspend', reason_id=reason_id, note=note)
            order._post_provisioning_signal('suspend', reason_id=reason_id, note=note)
        return True

    def action_resume_subscription(self):
        self._check_is_subscription()
        for order in self:
            if order.subscription_state != 'suspended':
                raise UserError(_("Only suspended subscriptions can be resumed."))
            order.write({
                'subscription_state': 'active',
                'suspension_reason_id': False,
                'suspension_note': False,
                'suspended_on': False,
                'suspended_by_id': False,
            })
            order._log_state_change('resume')
            order._post_provisioning_signal('resume')
        return True

    def action_cancel_subscription(self, reason_id=False, note=False):
        """Permanent termination. reason_id/note required by the UI wizard.

        Besides flipping the subscription to 'cancelled', this also triggers the
        standard sale "Cancel" button (action_cancel) so the underlying order is
        cancelled too, and from then on the order is frozen against further edits
        (see write())."""
        self._check_is_subscription()
        for order in self:
            if order.subscription_state in ('cancelled', 'closed'):
                continue
            # Run the whole termination under a flag that lets write() through
            # while we set the final state (after this, edits are blocked).
            order = order.with_context(subscription_lifecycle_write=True)
            # Call the standard "Cancel" button; skip its confirmation pop-up so
            # the termination completes in a single step.
            order.with_context(disable_cancel_warning=True).action_cancel()
            order.write({
                'subscription_state': 'cancelled',
                'cancellation_reason_id': reason_id or False,
                'cancellation_note': note or False,
                'cancelled_on': fields.Datetime.now(),
                'cancelled_by_id': self.env.uid,
            })
            order._log_state_change('cancel', reason_id=reason_id, note=note)
            order._post_provisioning_signal('cut_service', reason_id=reason_id, note=note)
        return True

    def _log_state_change(self, action, reason_id=False, note=False, line=False):
        self.ensure_one()
        return self.env['subscription.state.log'].create({
            'order_id': self.id,
            'order_line_id': line.id if line else False,
            'action': action,
            'reason_id': reason_id or False,
            'note': note or False,
        })

    # ---- UI launchers: open the reason wizard for suspend / cancel ----
    def action_open_suspend_wizard(self):
        self.ensure_one()
        self._check_is_subscription()
        if self.subscription_state != 'active':
            raise UserError(_("Only active subscriptions can be suspended."))
        return self._open_lifecycle_wizard('suspend', _('Suspend Subscription'))

    def action_open_cancel_wizard(self):
        self.ensure_one()
        self._check_is_subscription()
        if self.subscription_state in ('cancelled', 'closed'):
            raise UserError(_("This subscription is already cancelled or closed."))
        return self._open_lifecycle_wizard('cancel', _('Cancel Subscription'))

    def _open_lifecycle_wizard(self, mode, name):
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': 'subscription.lifecycle.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id, 'default_mode': mode},
        }

    # ------------------------------------------------------------------
    # Provisioning signal (extension hook)
    # ------------------------------------------------------------------
    def _post_provisioning_signal(self, action, line=None, reason_id=False, note=False):
        """Emit an operational signal (activate / suspend / cut service / pause line),
        carrying the disconnection/suspension reason.

        The default implementation logs the event and posts it to the chatter so
        the action is auditable. Override or extend this method to integrate with
        a real provisioning / telecom OSS (e.g. open or cut the actual lines, and
        relay reason.code to the OSS).
        """
        self.ensure_one()
        line_name = line.name if line else ''
        reason = self.env['subscription.reason'].browse(reason_id) if reason_id else False
        labels = {
            'activate': _("Service activation requested for all lines."),
            'suspend': _("Service suspension (temporary) requested for all lines."),
            'resume': _("Service re-activation requested for all lines."),
            'cut_service': _("Service disconnection requested for all lines."),
            'pause_line': _("Line paused (service suspended): %s") % line_name,
            'resume_line': _("Line resumed (service restored): %s") % line_name,
        }
        message = labels.get(action, action)
        if reason or note:
            detail = reason.name if reason else ''
            if note:
                detail = ("%s — %s" % (detail, note)) if detail else note
            message = _("%(msg)s\nReason: %(reason)s", msg=message, reason=detail)
        _logger.info("Subscription %s: provisioning signal '%s' (reason=%s)",
                     self.name, action, reason.code if reason else '-')
        self.message_post(body=message)
        return True

    # ------------------------------------------------------------------
    # Billing engine
    # ------------------------------------------------------------------
    def _get_subscription_invoice_partner(self):
        self.ensure_one()
        return self.partner_invoice_id or self.partner_id

    def _get_subscription_period_label(self, invoice_date):
        """Human-readable 'Subscription from <start> to <end>' for the cycle that
        starts on ``invoice_date`` (end = day before the next billing date)."""
        self.ensure_one()
        if not self.subscription_period_id or not invoice_date:
            return False
        next_date = self.subscription_period_id._get_next_date(invoice_date)
        end = (next_date - timedelta(days=1)) if next_date else invoice_date
        return _(
            "Subscription from %(start)s to %(end)s",
            start=format_date(self.env, invoice_date),
            end=format_date(self.env, end),
        )

    def _prepare_subscription_invoice_line_vals(self, line, period_label=None):
        self.ensure_one()
        # Delegate to the standard sale-line invoice preparation: it sets the
        # taxes correctly (mapped through the order's fiscal position), the income
        # account, analytic distribution, the per-period price and the
        # sale_line_ids link - exactly like a normal sale invoice. We only force
        # the quantity to the full line qty, because the standard `qty_to_invoice`
        # would be 0 after the first cycle for recurring lines.
        vals = line._prepare_invoice_line(quantity=line.product_uom_qty)
        # Recurring lines carry the covered period in their description.
        if period_label and line.subscription_line_type == 'recurring':
            base = vals.get('name') or line.name or line.product_id.display_name
            vals['name'] = "%s\n%s" % (base, period_label)
        return vals

    def _prepare_suspension_fee_invoice_line_vals(self, line, period_label=None):
        """Invoice-line vals for a PAUSED recurring line that still bills a reduced
        suspension fee. Reuses the standard prep (taxes/account/link), then
        overrides quantity/price/description to the flat per-cycle fee."""
        self.ensure_one()
        vals = line._prepare_invoice_line(quantity=1.0)
        vals['quantity'] = 1.0
        vals['price_unit'] = line.suspension_fee_amount
        base = vals.get('name') or line.name or line.product_id.display_name
        label = _("Suspension fee (line paused)")
        if line.pause_reason_id:
            label = "%s - %s" % (label, line.pause_reason_id.name)
        parts = [base, label]
        if period_label:
            parts.append(period_label)
        vals['name'] = "\n".join(parts)
        return vals

    def _collect_subscription_invoice_lines(self, period_label=None):
        """Build the invoice-line values due for the current cycle.

        Returns (line_vals, one_time_lines, pending_charges, paused_fee_lines):
          * active recurring lines (normal price),
          * paused recurring lines that charge a reduced suspension fee,
          * one-time lines not yet invoiced,
          * pending ad-hoc charges.
        """
        self.ensure_one()
        line_vals = []
        one_time_lines = self.env['sale.order.line']
        paused_fee_lines = self.env['sale.order.line']
        for line in self.order_line:
            if line.display_type or not line.product_id:
                continue
            if line.subscription_line_type != 'recurring':
                continue
            if line.subscription_line_state == 'active':
                line_vals.append(self._prepare_subscription_invoice_line_vals(line, period_label))
            elif (line.subscription_line_state == 'paused'
                  and line.charge_suspension_fee and line.suspension_fee_amount > 0):
                line_vals.append(self._prepare_suspension_fee_invoice_line_vals(line, period_label))
                paused_fee_lines |= line
            # else: paused with no fee -> skipped
        for line in self.order_line:
            if line.display_type or not line.product_id:
                continue
            if line.subscription_line_type == 'one_time' and not line.subscription_invoiced:
                line_vals.append(self._prepare_subscription_invoice_line_vals(line))
                one_time_lines |= line
        charges = self.subscription_charge_ids.filtered(lambda c: c.state == 'pending')
        for charge in charges:
            line_vals.append(charge._prepare_invoice_line_vals())
        return line_vals, one_time_lines, charges, paused_fee_lines

    def _advance_next_invoice_date(self):
        self.ensure_one()
        if not self.subscription_period_id:
            return
        base = self.subscription_next_invoice_date or fields.Date.context_today(self)
        next_date = self.subscription_period_id._get_next_date(base)
        self.subscription_next_invoice_date = next_date
        if self.subscription_end_date and next_date and next_date > self.subscription_end_date:
            self.subscription_state = 'closed'
            self._log_state_change('close')
            self._post_provisioning_signal('cut_service')

    def _generate_subscription_invoice(self, invoice_date=None, payment_term=None):
        """Create the invoice for the current cycle and advance the schedule.

        :param payment_term: optional account.payment.term to use for this invoice.
            When not provided, the subscription order's own payment terms are used.
        """
        self.ensure_one()
        if self.subscription_state != 'active':
            raise UserError(_("Only active subscriptions can be invoiced."))
        invoice_date = invoice_date or fields.Date.context_today(self)
        period_label = self._get_subscription_period_label(invoice_date)
        line_vals, one_time_lines, charges, paused_fee_lines = \
            self._collect_subscription_invoice_lines(period_label)
        if not line_vals:
            # Nothing billable this cycle (e.g. all recurring lines paused); still
            # move the schedule forward so the subscription does not get stuck.
            self._advance_next_invoice_date()
            return self.env['account.move']
        # Default payment terms = the subscription order's; overridable per invoice.
        term = self.payment_term_id if payment_term is None else payment_term
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self._get_subscription_invoice_partner().id,
            'invoice_origin': self.name,
            'subscription_order_id': self.id,
            'invoice_date': invoice_date,
            'currency_id': self.currency_id.id,
            'invoice_payment_term_id': term.id if term else False,
            # Carry the order's fiscal position so taxes are mapped/validated the
            # same way as on a normal customer invoice.
            'fiscal_position_id': self.fiscal_position_id.id or False,
            'invoice_line_ids': [(0, 0, vals) for vals in line_vals],
        })
        if one_time_lines:
            one_time_lines.write({'subscription_invoiced': True})
        if charges:
            charges.write({'state': 'invoiced', 'invoice_id': move.id})
        self._advance_next_invoice_date()
        return move

    def action_generate_subscription_invoice(self):
        """Manual billing: open the wizard to pick the invoice date / payment
        terms, then generate the invoice for the current cycle."""
        self.ensure_one()
        self._check_is_subscription()
        if self.subscription_state != 'active':
            raise UserError(_("Only active subscriptions can be invoiced."))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Generate Subscription Invoice'),
            'res_model': 'subscription.invoice.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
                'default_invoice_date': self.subscription_next_invoice_date or fields.Date.context_today(self),
                'default_payment_term_id': self.payment_term_id.id or False,
            },
        }

    def action_view_subscription_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Subscription Invoices'),
            'res_model': 'account.move',
            'domain': [('subscription_order_id', '=', self.id)],
            'view_mode': 'list,form',
            'context': {'create': False},
        }

    # ------------------------------------------------------------------
    # Link existing (historical) invoices to this subscription
    # ------------------------------------------------------------------
    def _get_linkable_invoice_domain(self, commercial=True):
        """Domain for existing customer invoices that MAY be linked to this
        subscription: same (commercial) partner, customer move, draft/posted,
        same company, and not already linked to any subscription."""
        self.ensure_one()
        if commercial:
            partner = self.partner_id.commercial_partner_id
            partner_dom = [('commercial_partner_id', '=', partner.id)]
        else:
            partner = self._get_subscription_invoice_partner()
            partner_dom = [('partner_id', '=', partner.id)]
        return partner_dom + [
            ('move_type', 'in', ('out_invoice', 'out_refund')),
            ('subscription_order_id', '=', False),
            ('company_id', '=', self.company_id.id),
            ('state', 'in', ('draft', 'posted')),
        ]

    def action_open_link_existing_invoices(self):
        self.ensure_one()
        self._check_is_subscription()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Link Existing Invoices'),
            'res_model': 'subscription.link.invoice.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id},
        }

    def action_view_partner_subscriptions(self):
        """Opens the customer's subscriptions (used from the partner smart button)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Subscriptions'),
            'res_model': 'sale.order',
            'domain': [('is_subscription', '=', True), ('partner_id', '=', self.partner_id.id)],
            'view_mode': 'list,form',
            'context': {'create': False},
        }

    # ------------------------------------------------------------------
    # Automated billing (Cron)
    # ------------------------------------------------------------------
    @api.model
    def _cron_generate_subscription_invoices(self):
        today = fields.Date.context_today(self)
        orders = self.search([
            ('is_subscription', '=', True),
            ('subscription_state', '=', 'active'),
            ('subscription_next_invoice_date', '!=', False),
            ('subscription_next_invoice_date', '<=', today),
        ])
        _logger.info("Subscription billing cron: %s subscription(s) due.", len(orders))
        for order in orders:
            guard = 0
            # Catch up any missed cycles (<= today), bounded by CATCH_UP_LIMIT.
            while (order.subscription_state == 'active'
                   and order.subscription_next_invoice_date
                   and order.subscription_next_invoice_date <= today
                   and guard < CATCH_UP_LIMIT):
                invoice_date = order.subscription_next_invoice_date
                try:
                    order._generate_subscription_invoice(invoice_date=invoice_date)
                except Exception as exc:  # noqa: BLE001 - never let one order kill the cron
                    _logger.exception(
                        "Subscription billing failed for %s: %s", order.name, exc)
                    break
                guard += 1
        return True
