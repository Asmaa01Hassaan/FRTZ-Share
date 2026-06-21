from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sale_order_type_id = fields.Many2one(
        "sale.order.type",
        string="Order Type",
        tracking=True,
        domain="['&', ('active', '=', True), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )

    order_type = fields.Char(
        string='Order Type',
        compute='_compute_order_type',
        store=True,
        readonly=True,
        tracking=True,
    )

    sale_order_type_name = fields.Char(
        related="sale_order_type_id.name",
        readonly=True,
    )

    # Exposes product type for order line contexts (Odoo 18 forbids parent.sale_order_type_id.product_type).
    sale_order_type_product_type = fields.Selection(
        related="sale_order_type_id.product_type",
        readonly=True,
    )
    sale_order_type_product_category_ids = fields.Many2many(
        related="sale_order_type_id.product_category_ids",
        readonly=True,
    )
    sale_order_type_classification = fields.Selection(
        related="sale_order_type_id.order_classification",
        readonly=True,
    )

    @api.depends('sale_order_type_id.name')
    def _compute_order_type(self):
        for order in self:
            order.order_type = order.sale_order_type_id.name or False

    @api.depends(
        "sale_order_type_id",
        "sale_order_type_id.sale_order_template_id",
    )
    def _compute_sale_order_template_id(self):
        super()._compute_sale_order_template_id()
        for order in self:
            if "website_id" in order._fields and order.website_id:
                continue
            type_template = order.sale_order_type_id.sale_order_template_id
            if type_template:
                order.sale_order_template_id = type_template

    @api.depends(
        "sale_order_type_id",
        "sale_order_type_id.journal_id",
    )
    def _compute_journal_id(self):
        super()._compute_journal_id()
        for order in self:
            if order.sale_order_type_id.journal_id:
                order.journal_id = order.sale_order_type_id.journal_id

    @api.depends(
        "pricelist_id",
        "pricelist_id.currency_id",
        "company_id",
        "sale_order_type_id",
        "sale_order_type_id.currency_id",
    )
    def _compute_currency_id(self):
        for order in self:
            sot = order.sale_order_type_id
            if sot and sot.currency_id:
                order.currency_id = sot.currency_id
            else:
                order.currency_id = order.pricelist_id.currency_id or order.company_id.currency_id

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Ensure New from dynamic menu applies the type (context keys are not always merged early enough)
        tid = self.env.context.get("default_sale_order_type_id")
        if tid and "sale_order_type_id" in fields_list:
            res["sale_order_type_id"] = tid
        if tid:
            sot = self.env["sale.order.type"].browse(tid)
            if sot.exists():
                if "company_id" in fields_list and sot.company_id:
                    res["company_id"] = sot.company_id.id
                if "sale_order_template_id" in fields_list and sot.sale_order_template_id:
                    res["sale_order_template_id"] = sot.sale_order_template_id.id
        return res

    def _line_product_type(self, line):
        """Return product type without triggering record rules on line products."""
        Product = self.env["product.product"].sudo()
        Template = self.env["product.template"].sudo()

        def _record_id(field_name):
            value = line._cache.get(line._fields[field_name])
            if not value and line._origin:
                value = line._origin._cache.get(line._origin._fields[field_name])
            if not value:
                return False
            return value.id if hasattr(value, "id") else value

        product_id = _record_id("product_id")
        if product_id:
            product = Product.browse(product_id)
            return product.type if product.exists() else False

        template_id = _record_id("product_template_id")
        if template_id:
            template = Template.browse(template_id)
            return template.type if template.exists() else False
        return False

    def _line_product_categ(self, line):
        """Return product category without triggering record rules on line products."""
        Product = self.env["product.product"].sudo()
        Template = self.env["product.template"].sudo()

        def _record_id(field_name):
            value = line._cache.get(line._fields[field_name])
            if not value and line._origin:
                value = line._origin._cache.get(line._origin._fields[field_name])
            if not value:
                return False
            return value.id if hasattr(value, "id") else value

        product_id = _record_id("product_id")
        if product_id:
            product = Product.browse(product_id)
            return product.categ_id if product.exists() else False

        template_id = _record_id("product_template_id")
        if template_id:
            template = Template.browse(template_id)
            return template.categ_id if template.exists() else False
        return False

    def _clear_incompatible_order_lines_for_product_type(self):
        sot = self.sale_order_type_id
        if not sot:
            return
        pt = sot.product_type
        restrict_categories = bool(sot.product_category_ids)
        for line in self.order_line:
            if line.display_type:
                continue
            incompatible = False
            if pt:
                tmpl_type = self._line_product_type(line)
                if tmpl_type and tmpl_type != pt:
                    incompatible = True
            if not incompatible and restrict_categories:
                categ = self._line_product_categ(line)
                if not sot._is_category_allowed(categ):
                    incompatible = True
            if incompatible:
                line.update({"product_id": False, "product_template_id": False})

    @api.onchange("sale_order_template_id")
    def _onchange_sale_order_template_id(self):
        return super(
            SaleOrder,
            self.with_context(skip_sale_order_product_type_search=True),
        )._onchange_sale_order_template_id()

    @api.onchange("sale_order_type_id")
    def _onchange_sale_order_type_id(self):
        """Apply company/currency from type, align pricelist when possible, clear incompatible lines."""
        if self.sale_order_type_id:
            sot = self.sale_order_type_id
            if sot.company_id:
                self.company_id = sot.company_id
            if sot.currency_id:
                partner_pl = (
                    self.partner_id.property_product_pricelist if self.partner_id else False
                )
                if partner_pl and partner_pl.currency_id == sot.currency_id:
                    self.pricelist_id = partner_pl
                else:
                    pl = self.env["product.pricelist"].search(
                        [
                            ("currency_id", "=", sot.currency_id.id),
                            "|",
                            ("company_id", "=", False),
                            ("company_id", "=", self.company_id.id),
                        ],
                        limit=1,
                    )
                    if pl:
                        self.pricelist_id = pl
            if sot.journal_id:
                self.journal_id = sot.journal_id
            if sot.sale_order_template_id:
                self.sale_order_template_id = sot.sale_order_template_id
                self._onchange_sale_order_template_id()
            else:
                self._clear_incompatible_order_lines_for_product_type()
        else:
            self._clear_incompatible_order_lines_for_product_type()

    def write(self, vals):
        res = super().write(vals)
        if vals.get("sale_order_type_id"):
            for order in self:
                sot = order.sale_order_type_id
                if sot and sot.company_id and order.company_id != sot.company_id:
                    super(SaleOrder, order).write({"company_id": sot.company_id.id})
        return res

    @api.model
    def _resolve_sale_order_type_id(self, vals):
        sot_id = vals.get("sale_order_type_id")
        if isinstance(sot_id, models.Model):
            sot_id = sot_id.id
        if not sot_id:
            sot_id = self.env.context.get("default_sale_order_type_id")
        return sot_id

    @api.model
    def _assign_order_name_from_type(self, vals):
        """Assign SO name from the sale order type's own ir.sequence."""
        if vals.get("name", "New") != _("New"):
            return True
        sot_id = self._resolve_sale_order_type_id(vals)
        if not sot_id:
            return False
        sot = self.env["sale.order.type"].browse(sot_id)
        if not sot.exists():
            return False
        vals.setdefault("sale_order_type_id", sot.id)
        seq_date = None
        if vals.get("date_order"):
            seq_date = fields.Datetime.context_timestamp(
                self, fields.Datetime.to_datetime(vals["date_order"])
            )
        name = sot._get_next_order_name(sequence_date=seq_date)
        if name:
            vals["name"] = name
            return True
        return False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            sot_id = self._resolve_sale_order_type_id(vals)
            if sot_id:
                sot = self.env["sale.order.type"].browse(sot_id)
                if sot.exists() and sot.company_id:
                    vals["company_id"] = sot.company_id.id
            if not self._assign_order_name_from_type(vals) and vals.get("name", "New") == _("New"):
                try:
                    seq_date = fields.Datetime.context_timestamp(
                        self, fields.Datetime.to_datetime(vals.get("date_order"))
                    ) if vals.get("date_order") else None
                    vals["name"] = self.env["ir.sequence"].next_by_code(
                        "sale.order", sequence_date=seq_date
                    ) or _("New")
                except Exception:
                    vals["name"] = self.env["ir.sequence"].next_by_code("sale.order") or _("New")
        return super().create(vals_list)

    def _should_skip_sale_journal_type_validation(self):
        self.ensure_one()
        sot = self.sale_order_type_id
        return bool(sot and sot.journal_incactive_validation)

    def _create_account_invoices(self, invoice_vals_list, final):
        orders = self
        skip_validation = False
        if len(orders) == 1:
            skip_validation = orders._should_skip_sale_journal_type_validation()
        elif orders and all(order._should_skip_sale_journal_type_validation() for order in orders):
            skip_validation = True
        if skip_validation:
            orders = orders.with_context(skip_sale_journal_type_validation=True)
        return super(SaleOrder, orders)._create_account_invoices(invoice_vals_list, final)

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        if self.sale_order_type_id.journal_id:
            invoice_vals["journal_id"] = self.sale_order_type_id.journal_id.id
        return invoice_vals
