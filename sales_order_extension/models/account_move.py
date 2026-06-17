# -*- coding: utf-8 -*-

from odoo import api, models, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _bypass_sale_journal_type_validation(self):
        self.ensure_one()
        if self.env.context.get("skip_sale_journal_type_validation"):
            return True
        orders = self.invoice_line_ids.sale_line_ids.order_id
        if not orders and self.invoice_origin:
            origin_names = [
                name.strip()
                for name in (self.invoice_origin or "").split(",")
                if name.strip()
            ]
            if origin_names:
                orders = self.env["sale.order"].search([("name", "in", origin_names)])
        return any(
            order.sale_order_type_id.journal_incactive_validation
            for order in orders
            if order.sale_order_type_id
        )

    @api.constrains("journal_id", "move_type")
    def _check_journal_move_type(self):
        bypassed = self.browse()
        for move in self:
            if (
                move.is_sale_document(include_receipts=True)
                and move.journal_id.type != "sale"
                and move._bypass_sale_journal_type_validation()
            ):
                bypassed |= move
        remaining = self - bypassed
        if remaining:
            return super(AccountMove, remaining)._check_journal_move_type()
