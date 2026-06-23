import re

from odoo import api, fields, models, _


class SaleOrderType(models.Model):
    _name = "sale.order.type"
    _description = "Sale Order Type"
    _order = "name"

    name = fields.Char(required=True, translate=True)

    order_classification = fields.Selection(
        [
            ("sale", "Sale Order"),
            ("subscription", "Subscription"),
        ],
        string="Order Classification",
        default="sale",
        required=True,
        help="Subscription features apply only when this type is Subscription.",
    )

    product_type = fields.Selection(
        [
            ("consu", "Goods"),
            ("service", "Service"),
            ("combo", "Combo"),
        ],
        string="Product Type",
        default="consu",
        required=True,
        help="Same categories as on products: goods, service, or combo.",
    )

    active = fields.Boolean(default=True)

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        index=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Invoicing Journal",
        domain="[('type', 'in', ('sale', 'general')), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
        help="Default journal for invoices created from orders of this type (Sales or Miscellaneous only).",
    )
    journal_incactive_validation = fields.Boolean(
        string="Skip Sale Journal Validation",
        default=False,
        help="When enabled, customer invoices from this order type may use a non-sale "
            "journal (e.g. Miscellaneous) without raising a validation error.",
    )
    product_category_ids = fields.Many2many(
        "product.category",
        "sale_order_type_product_category_rel",
        "sale_order_type_id",
        "category_id",
        string="Product Categories",
        help="When set, only products in these categories (including subcategories) "
            "can be added to orders of this type. Leave empty to allow all categories.",
    )
    sale_order_template_id = fields.Many2one(
        "sale.order.template",
        string="Quotation Template",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
        help="Default quotation template applied to new orders of this type.",
    )

    sequence_prefix = fields.Char(
        string="Sequence Prefix",
        required=True,
        default="SO/%(year)s/",
        help="Prefix for order numbers of this type, e.g. SOI/%(year)s/. "
            "Supports Odoo placeholders: %(year)s, %(month)s, %(day)s, etc.",
    )
    sequence_code = fields.Char(
        string="Sequence Code",
        help="Technical code on ir.sequence (e.g. custom.sale.order). "
            "Leave empty to use an auto code sale.order.type.<id>.",
        copy=False,
    )
    sequence_padding = fields.Integer(
        string="Sequence Size",
        default=5,
        help="Number of digits for the numeric part (e.g. 5 → 00001).",
    )

    sequence_auto = fields.Boolean(
        string="Auto-generated sequence",
        default=False,
        readonly=True,
        copy=False,
    )

    sequence_id = fields.Many2one(
        "ir.sequence",
        string="Sequence",
        readonly=True,
        copy=False,
        ondelete="set null",
    )

    action_id = fields.Many2one("ir.actions.act_window", readonly=True, copy=False, ondelete="set null")
    menu_id = fields.Many2one("ir.ui.menu", readonly=True, copy=False, ondelete="set null")

    menu_parent_id = fields.Many2one(
        "ir.ui.menu",
        string="Parent Menu",
        ondelete="set null",
        help="Where this type's menu appears. Leave empty to group it under "
            "'Sales Order Types' (inside Sales > Orders). Pick 'Sales' to make "
            "it a top-level menu next to Orders.",
    )
    menu_sequence = fields.Integer(
        string="Menu Sequence",
        help="Position of the menu among its siblings (smaller = higher). "
            "Leave 0 for an automatic value. For reference: Orders is 10, "
            "Subscriptions is 15 - use e.g. 11 to sit right after Orders.",
    )
    sales_menu_root_id = fields.Integer(
        string="Sales App Menu Root",
        compute="_compute_sales_menu_root_id",
        help="Technical: id of the Sales app root menu, used to limit the "
            "Parent Menu choices to menus inside the Sales app only.",
    )

    def _compute_sales_menu_root_id(self):
        root = self.env.ref("sale.sale_menu_root", raise_if_not_found=False)
        root_id = root.id if root else False
        for rec in self:
            rec.sales_menu_root_id = root_id

    _sql_constraints = [
        ("name_uniq", "unique(name)", "This sale order type name already exists."),
    ]

    def _is_category_allowed(self, category):
        """Return True if category is empty restriction or product category is within allowed tree."""
        self.ensure_one()
        if not self.product_category_ids:
            return True
        if not category:
            return False
        return bool(
            category.id in self.env["product.category"]
            .search([("id", "child_of", self.product_category_ids.ids)])
            .ids
        )

    def _product_category_domain(self):
        self.ensure_one()
        if not self.product_category_ids:
            return []
        allowed = self.env["product.category"].search(
            [("id", "child_of", self.product_category_ids.ids)]
        ).ids
        return [("categ_id", "in", allowed)] if allowed else [("categ_id", "=", False)]

    @api.model
    def _suggest_sequence_prefix(self, name, order_classification=None):
        """Default prefix hints aligned with account_invoice_installments sequences."""
        if order_classification == "subscription":
            return "SOS/%(year)s/"
        n = (name or "").lower()
        if any(k in n for k in ("custom", "warehouse", "مستودع")):
            return "SOI/%(year)s/"
        if any(k in n for k in ("wholesale", "external", "خارجي", "بيع خارج")):
            return "SOG/%(year)s/"
        if any(k in n for k in ("subscription", "اشتراك", "خدمة")):
            return "SOS/%(year)s/"
        if any(k in n for k in ("standard", "قياسي", "عادي")):
            return "SOS/%(year)s/"
        slug = re.sub(r"[^A-Za-z0-9]+", "", name.strip()).upper()[:3] or "SO"
        # %% keeps a literal %(year)s placeholder for ir.sequence to interpolate
        # later; a bare %(year)s here would make % treat slug as a mapping.
        return "%s/%%(year)s/" % slug

    def _sequence_technical_code(self):
        self.ensure_one()
        return self.sequence_code or "sale.order.type.%s" % self.id

    def _sequence_values(self):
        self.ensure_one()
        return {
            "name": self.name,
            "code": self._sequence_technical_code(),
            "prefix": self.sequence_prefix or "SO/%(year)s/",
            "padding": self.sequence_padding or 5,
            "number_next": 1,
            "implementation": "standard",
            "company_id": self.company_id.id if self.company_id else False,
        }

    @api.onchange("name")
    def _onchange_name_sequence_prefix(self):
        if self.name and not self.sequence_prefix:
            self.sequence_prefix = self._suggest_sequence_prefix(
                self.name, self.order_classification
            )

    @api.onchange("order_classification")
    def _onchange_order_classification(self):
        if self.order_classification == "subscription":
            self.product_type = "service"
            if not self.sequence_prefix or self.sequence_prefix == "SO/%(year)s/":
                self.sequence_prefix = "SOS/%(year)s/"
        elif self.sequence_prefix == "SOS/%(year)s/":
            self.sequence_prefix = self._suggest_sequence_prefix(self.name, "sale")

    @api.model
    def _apply_classification_defaults(self, vals):
        if vals.get("order_classification") == "subscription":
            vals.setdefault("product_type", "service")
            if not vals.get("sequence_prefix"):
                vals["sequence_prefix"] = self._suggest_sequence_prefix(
                    vals.get("name"), "subscription"
                )

    def _ensure_sequence(self):
        IrSequence = self.env["ir.sequence"].sudo()
        for rec in self:
            if not rec.name:
                continue
            vals = rec._sequence_values()
            code = vals["code"]
            if rec.sequence_id:
                rec.sequence_id.sudo().write(
                    {
                        "name": vals["name"],
                        "code": code,
                        "prefix": vals["prefix"],
                        "padding": vals["padding"],
                        "company_id": vals["company_id"],
                    }
                )
                continue
            existing = IrSequence.search([("code", "=", code)], limit=1)
            if existing:
                existing.sudo().write(
                    {
                        "name": vals["name"],
                        "prefix": vals["prefix"],
                        "padding": vals["padding"],
                        "company_id": vals["company_id"],
                    }
                )
                rec.write({"sequence_id": existing.id, "sequence_auto": True})
                continue
            seq = IrSequence.create(vals)
            rec.write({"sequence_id": seq.id, "sequence_auto": True})

    def _get_next_order_name(self, sequence_date=None):
        """Return the next order number using this type's dedicated sequence."""
        self.ensure_one()
        self._ensure_sequence()
        if not self.sequence_id:
            return False
        return self.sequence_id.next_by_id(sequence_date=sequence_date)

    def _sync_default_search_filter(self):
        """Do NOT keep a saved default search filter on the type's screen.

        The action's own domain already restricts records to this type, so a
        default ir.filters would only show a redundant (starred) facet in the
        search bar. Remove any leftover filter previously created for the action.
        """
        IrFilters = self.env["ir.filters"].sudo()
        actions = self.mapped("action_id")
        if not actions:
            return
        leftovers = IrFilters.search([("action_id", "in", actions.ids)])
        if leftovers:
            leftovers.unlink()

    def _ensure_dynamic_menu_and_action(self):
        default_parent = self.env.ref("sales_order_extension.menu_frtz_root_sales")
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

            # NB: no "search_default_sale_order_type_id" - the action domain below
            # already restricts records to this type without showing a search facet.
            ctx = {
                "default_sale_order_type_id": rec.id,
                "restrict_order_product_type": rec.product_type,
                "restrict_order_classification": rec.order_classification,
            }
            if rec.product_category_ids:
                ctx["restrict_order_product_category_ids"] = rec.product_category_ids.ids
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

            parent = rec.menu_parent_id or default_parent
            menu_vals = {
                "name": rec.name,
                "parent_id": parent.id,
                "sequence": rec.menu_sequence or min(rec.id * 10, 2**15 - 1),
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
        for vals in vals_list:
            if vals.get("name") and not vals.get("sequence_prefix"):
                vals["sequence_prefix"] = self._suggest_sequence_prefix(
                    vals["name"], vals.get("order_classification")
                )
            self._apply_classification_defaults(vals)
        records = super().create(vals_list)
        records._ensure_sequence()
        records._ensure_dynamic_menu_and_action()
        return records

    def write(self, vals):
        res = super().write(vals)
        if any(
            k in vals
            for k in (
                "name",
                "active",
                "company_id",
                "product_type",
                "product_category_ids",
                "sequence_prefix",
                "sequence_code",
                "sequence_padding",
                "order_classification",
                "menu_parent_id",
                "menu_sequence",
            )
        ):
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
