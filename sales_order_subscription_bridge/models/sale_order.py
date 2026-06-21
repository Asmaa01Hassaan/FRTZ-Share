import datetime
from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from odoo.addons.sttl_sale_subscription.models.sale import Sale as SttlSaleOrder


class SaleOrder(models.Model):
    _inherit = "sale.order"

    is_subscription_order = fields.Boolean(
        string="Is Subscription Order",
        compute="_compute_is_subscription_order",
        store=True,
    )

    @api.depends("sale_order_type_id", "sale_order_type_id.order_classification")
    def _compute_is_subscription_order(self):
        for order in self:
            order.is_subscription_order = (
                order.sale_order_type_id.order_classification == "subscription"
            )

    def _validate_subscription_product_mix(self):
        for order in self:
            recurring = non_recurring = False
            for line in order.order_line:
                if not line.product_id:
                    continue
                if line.product_id.is_recurring:
                    recurring = True
                else:
                    non_recurring = True
            if recurring and non_recurring:
                raise UserError(
                    _("Currently we don't support recurring and non recurring products together")
                )

    @api.onchange("order_line")
    def onchange_line_ids(self):
        if not self.is_subscription_order:
            return
        return super().onchange_line_ids()

    @api.model_create_multi
    def create(self, vals_list):
        orders = super(SttlSaleOrder, self).create(vals_list)
        orders.filtered("is_subscription_order")._validate_subscription_product_mix()
        return orders

    def write(self, vals):
        res = super(SttlSaleOrder, self).write(vals)
        if "order_line" in vals or "sale_order_type_id" in vals:
            self.filtered("is_subscription_order")._validate_subscription_product_mix()
        return res

    def _subscription_type_domain(self):
        return [("sale_order_type_id.order_classification", "=", "subscription")]

    def action_create_recurring_invoices(self):
        for order in self:
            if not order.is_subscription_order:
                raise UserError(_("Recurring invoices are only available on subscription order types."))
        return super().action_create_recurring_invoices()

    def end_subscription(self):
        for order in self:
            if not order.is_subscription_order:
                raise UserError(_("This action is only available on subscription order types."))
        return super().end_subscription()

    def renew_subscription(self):
        for order in self:
            if not order.is_subscription_order:
                raise UserError(_("This action is only available on subscription order types."))
        return super().renew_subscription()

    def generate_recurring_invoices(self):
        domain = [
            ("next_invoice_date", "=", datetime.datetime.today().date()),
            ("state", "=", "sale"),
            ("subscription_status", "=", "b"),
        ] + self._subscription_type_domain()
        orders = self.env["sale.order"].search(domain)
        for order in orders:
            do_copied = False
            do_cpy = False
            for line in order.order_line:
                if (
                    not do_copied
                    and line.product_id.is_recurring
                    and line.invoice_status != "to invoice"
                ):
                    if line.product_id.type != "service":
                        do_cpy = line.move_ids[0].picking_id.copy()
                        do_cpy.state = "assigned"
                        do_copied = True
                        for move in do_cpy.move_ids_without_package:
                            move.quantity = move.product_uom_qty
                    else:
                        if line.product_id.invoice_policy == "order":
                            if not line.prev_added_qty:
                                line.prev_added_qty = line.product_uom_qty
                            line.product_uom_qty = line.product_uom_qty + line.prev_added_qty
                        else:
                            line.qty_delivered += line.product_uom_qty
                if line.product_id.invoice_policy == "order":
                    qty = False
                    if do_cpy:
                        for do_cpy_line in do_cpy.move_ids_without_package:
                            if do_cpy_line.product_id == line.product_id:
                                qty = do_cpy_line.product_uom_qty
                        line.product_uom_qty += qty
                        self.action_invoice(order)
            self.action_invoice(order)
            if order.recurr_until and order.next_invoice_date:
                if order.recurr_until <= order.next_invoice_date:
                    order.subscription_status = "c"

    def send_notification(self):
        default_duration = 10
        domain = [
            ("next_invoice_date", "!=", False),
            ("subscription_status", "=", "b"),
        ] + self._subscription_type_domain()
        sale_orders = self.search(domain)
        notification_duration = self.env["ir.config_parameter"].get_param(
            "sttl_sale_subscription.notification_duration"
        )
        if notification_duration is False:
            notification_duration = default_duration
        for order in sale_orders:
            date_diff = (order.next_invoice_date - date.today()).days
            if int(notification_duration) == date_diff:
                template_id = self.env.ref(
                    "sttl_sale_subscription.sale_subscription_notification_template"
                ).id
                template = self.env["mail.template"].browse(template_id)
                template.send_mail(order.id, force_send=True)
