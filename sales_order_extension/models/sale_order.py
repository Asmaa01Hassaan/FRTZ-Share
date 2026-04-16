from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sale_order_type_id = fields.Many2one(
        "sale.order.type",
        string=_("Order Type"),
        tracking=True,
        domain="['&', ('active', '=', True), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )

    order_type = fields.Char(
        string=_('Order Type'),
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

    @api.depends('sale_order_type_id.name')
    def _compute_order_type(self):
        for order in self:
            order.order_type = order.sale_order_type_id.name or False

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
        if tid and "company_id" in fields_list:
            sot = self.env["sale.order.type"].browse(tid)
            if sot.exists() and sot.company_id:
                res["company_id"] = sot.company_id.id
        return res

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
        pt = self.sale_order_type_id.product_type if self.sale_order_type_id else False
        if not pt:
            return
        for line in self.order_line:
            if line.display_type:
                continue
            mismatch = False
            if line.product_id and line.product_id.type != pt:
                mismatch = True
            elif line.product_template_id and line.product_template_id.type != pt:
                mismatch = True
            if mismatch:
                line.product_id = False
                line.product_template_id = False

    def write(self, vals):
        res = super().write(vals)
        if vals.get("sale_order_type_id"):
            for order in self:
                sot = order.sale_order_type_id
                if sot and sot.company_id and order.company_id != sot.company_id:
                    super(SaleOrder, order).write({"company_id": sot.company_id.id})
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            sot_id = vals.get("sale_order_type_id")
            if sot_id:
                sot = self.env["sale.order.type"].browse(sot_id)
                if sot.company_id:
                    vals["company_id"] = sot.company_id.id
            if vals.get('name', _('New')) == _('New'):
                if sot_id:
                    sot = self.env["sale.order.type"].browse(sot_id)
                    if sot.sequence_id:
                        try:
                            seq_date = fields.Datetime.context_timestamp(
                                self, fields.Datetime.to_datetime(vals.get('date_order'))
                            ) if vals.get('date_order') else None
                            vals["name"] = sot.sequence_id.next_by_id(sequence_date=seq_date) or _('New')
                            continue
                        except Exception:
                            pass
                try:
                    seq_date = fields.Datetime.context_timestamp(
                        self, fields.Datetime.to_datetime(vals.get('date_order'))
                    ) if vals.get('date_order') else None
                    vals['name'] = self.env['ir.sequence'].next_by_code(
                        'sale.order', sequence_date=seq_date
                    ) or _('New')
                except Exception:
                    vals['name'] = self.env['ir.sequence'].next_by_code('sale.order') or _('New')
        return super().create(vals_list)
