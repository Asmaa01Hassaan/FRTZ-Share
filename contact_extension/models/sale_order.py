from odoo import api, fields, models, Command


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    customer_guarantees_ids = fields.Many2many(
        'res.partner',
        'sale_order_customer_guarantees_rel',
        'sale_order_id',
        'partner_id',
        string='Customer Guarantees',
        help='Select customers who will act as guarantees for this sale order',
    )

    customer_guarantees_list_ids = fields.One2many(
        'customer.guarantees',
        'sale_order_id',
        string='Customer Guarantees List',
    )

    guarantees_count = fields.Integer(
        string='Guarantees Count',
        compute='_compute_guarantees_count',
    )

    @api.depends('customer_guarantees_list_ids', 'customer_guarantees_ids')
    def _compute_guarantees_count(self):
        for order in self:
            order.guarantees_count = len(
                order.customer_guarantees_list_ids or order.customer_guarantees_ids
            )

    def _sync_guarantees_many2many_from_list(self):
        for order in self:
            order.customer_guarantees_ids = [
                Command.set(order.customer_guarantees_list_ids.mapped('customer_id').ids)
            ]

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        guarantee_lines = self.customer_guarantees_list_ids
        if not guarantee_lines:
            return invoice_vals

        invoice_vals['customer_guarantees_ids'] = [
            Command.set(guarantee_lines.mapped('customer_id').ids)
        ]
        invoice_vals['customer_guarantees_list_ids'] = [
            Command.create({
                'customer_id': line.customer_id.id,
                'sale_order_customer_guarantees_status': line.sale_order_customer_guarantees_status,
                'notes': line.notes,
                'date': line.date,
            })
            for line in guarantee_lines
        ]
        return invoice_vals
