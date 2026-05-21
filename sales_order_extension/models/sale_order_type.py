import re

from odoo import api, fields, models, _


class SaleOrderType(models.Model):
    _name = "sale.order.type"
    _description = "Sale Order Type"
    _order = "name"

    name = fields.Char(required=True, translate=True)

    product_type = fields.Selection(
        [
            ("consu", _("Goods")),
            ("service", _("Service")),
            ("combo", _("Combo")),
        ],
        string=_("Product Type"),
        default="consu",
        required=True,
        help=_("Same categories as on products: goods, service, or combo."),
    )

    active = fields.Boolean(default=True)

    company_id = fields.Many2one(
        "res.company",
        string=_("Company"),
        default=lambda self: self.env.company,
        index=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string=_("Currency"),
        default=lambda self: self.env.company.currency_id,
    )

    sequence_auto = fields.Boolean(
        string=_("Auto-generated sequence"),
        default=False,
        readonly=True,
        copy=False,
    )

    sequence_id = fields.Many2one(
        "ir.sequence",
        string=_("Sequence"),
        readonly=True,
        copy=False,
        ondelete="set null",
    )

    action_id = fields.Many2one("ir.actions.act_window", readonly=True, copy=False, ondelete="set null")
    menu_id = fields.Many2one("ir.ui.menu", readonly=True, copy=False, ondelete="set null")

    _sql_constraints = [
        ("name_uniq", "unique(name)", "This sale order type name already exists."),
    ]

    @api.model
    def _sequence_prefix_from_name(self, name):
        if not name:
            return "SO-"
        slug = re.sub(r"[^A-Za-z0-9]+", "-", name.strip())
        slug = slug.strip("-").upper()[:12] or "SO"
        return "%s-" % slug

    def _ensure_sequence(self):
        IrSequence = self.env["ir.sequence"].sudo()
        for rec in self:
            if not rec.name:
                continue
            code = "sale.order.type.%s" % rec.id
            if rec.sequence_id:
                rec.sequence_id.sudo().write(
                    {
                        "name": rec.name,
                        "prefix": self._sequence_prefix_from_name(rec.name),
                        "company_id": rec.company_id.id if rec.company_id else False,
                    }
                )
                continue
            existing = IrSequence.search([("code", "=", code)], limit=1)
            if existing:
                rec.write({"sequence_id": existing.id, "sequence_auto": True})
                continue
            seq = IrSequence.create(
                {
                    "name": rec.name,
                    "code": code,
                    "prefix": self._sequence_prefix_from_name(rec.name),
                    "padding": 5,
                    "number_next": 1,
                    "implementation": "standard",
                    "company_id": rec.company_id.id if rec.company_id else False,
                }
            )
            rec.write({"sequence_id": seq.id, "sequence_auto": True})

    def _sync_default_search_filter(self):
        IrFilters = self.env["ir.filters"].sudo()
        for rec in self:
            if not rec.action_id:
                continue
            if not rec.active:
                filt = IrFilters.search([("action_id", "=", rec.action_id.id)], limit=1)
                if filt:
                    filt.write({"active": False})
                continue

            domain_str = str([("sale_order_type_id", "=", rec.id)])
            vals = {
                "name": rec.name,
                "model_id": "sale.order",
                "domain": domain_str,
                "context": "{}",
                "sort": "[]",
                "action_id": rec.action_id.id,
                "is_default": True,
                "user_id": False,
                "active": True,
            }
            filt = IrFilters.search([("action_id", "=", rec.action_id.id)], limit=1)
            if filt:
                filt.write(vals)
            else:
                IrFilters.create(vals)

    def _ensure_dynamic_menu_and_action(self):
        parent = self.env.ref("sales_order_extension.menu_frtz_root_sales")
        search_view = self.env.ref(
            "sales_order_extension.view_sales_order_filter_custom",
            raise_if_not_found=False,
        )

        for rec in self:
            if not rec.active:
                if rec.menu_id:
                    rec.menu_id.sudo().write({"active": False})
                rec._sync_default_search_filter()
                continue

            ctx = {
                "default_sale_order_type_id": rec.id,
                "search_default_sale_order_type_id": rec.id,
                "restrict_order_product_type": rec.product_type,
            }
            action_vals = {
                "name": rec.name,
                "res_model": "sale.order",
                "view_mode": "list,form,kanban,calendar,pivot,graph",
                "domain": str([("sale_order_type_id", "=", rec.id)]),
                "context": str(ctx),
            }
            if search_view:
                action_vals["search_view_id"] = search_view.id

            if rec.action_id:
                rec.action_id.sudo().write(action_vals)
            else:
                rec.action_id = self.env["ir.actions.act_window"].sudo().create(action_vals).id

            menu_vals = {
                "name": rec.name,
                "parent_id": parent.id,
                "sequence": min(rec.id * 10, 2**15 - 1),
                "action": "ir.actions.act_window,%s" % rec.action_id.id,
                "active": True,
            }
            if rec.menu_id:
                rec.menu_id.sudo().write(menu_vals)
            else:
                rec.menu_id = self.env["ir.ui.menu"].sudo().create(menu_vals).id

            rec._sync_default_search_filter()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._ensure_sequence()
        records._ensure_dynamic_menu_and_action()
        return records

    def write(self, vals):
        res = super().write(vals)
        if any(k in vals for k in ("name", "active", "company_id", "product_type")):
            self._ensure_sequence()
            self._ensure_dynamic_menu_and_action()
        return res

    def unlink(self):
        menus = self.mapped("menu_id")
        actions = self.mapped("action_id")
        seqs = self.filtered(lambda r: r.sequence_auto and r.sequence_id).mapped("sequence_id")
        filters = self.env["ir.filters"].sudo().search([("action_id", "in", actions.ids)])
        if filters:
            filters.unlink()
        if menus:
            menus.sudo().unlink()
        if actions:
            actions.sudo().unlink()
        res = super().unlink()
        if seqs:
            seqs.sudo().unlink()
        return res
