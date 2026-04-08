from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    vendor_name_id = fields.Many2one('res.partner', string=_('Vendor Name'))
    payment_type = fields.Selection(
        [
            ('immediate', _('Immediate Payment')),
            ('regular', _('Regular Installments')),
            ('irregular', _('Irregular Installments')),
        ],
        string=_("Payment plan"),
        default="immediate",
        tracking=True,
        copy=False,
        help=_("Select the payment plan for this order")
    )

    # Mirrors sale_order_type_id.name for search / display (same label as "Order Type")
    order_type = fields.Char(
        string=_('Order Type'),
        compute='_compute_order_type',
        store=True,
        readonly=True,
        tracking=True,
    )

    sale_order_type_id = fields.Many2one(
        "sale.order.type",
        string=_("Order Type"),
        tracking=True,
        domain="[('active', '=', True)]",
    )

    sale_order_type_name = fields.Char(
        related="sale_order_type_id.name",
        readonly=True,
    )

    @api.depends('sale_order_type_id.name')
    def _compute_order_type(self):
        for order in self:
            order.order_type = order.sale_order_type_id.name or False

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Ensure New from dynamic menu applies the type (context keys are not always merged early enough)
        tid = self.env.context.get("default_sale_order_type_id")
        if tid and "sale_order_type_id" in fields_list:
            res["sale_order_type_id"] = tid
        return res

    @api.onchange("sale_order_type_id")
    def _onchange_sale_order_type_id_clear_mismatching_products(self):
        """When the order type (and thus product type) changes, drop line products that no longer match."""
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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                sot_id = vals.get("sale_order_type_id")
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
