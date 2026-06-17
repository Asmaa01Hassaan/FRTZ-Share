from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CustomerGuarantees(models.Model):
    _name = 'customer.guarantees'
    _description = 'Customer Guarantees'
    _rec_name = 'customer_id'

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        ondelete='cascade',
    )

    account_move_id = fields.Many2one(
        'account.move',
        string='Invoice',
        ondelete='cascade',
    )

    customer_id = fields.Many2one(
        'res.partner',
        string='Customer Name',
        required=True,
        domain="[('customer_rank', '>', 0)]",
    )

    sale_order_customer_guarantees_status = fields.Selection(
        [
            ('active', 'Active'),
            ('suspended', 'Suspended'),
        ],
        string='Status',
        default='active',
        required=True,
    )

    notes = fields.Text(string='Notes')
    date = fields.Date(string='Date', default=fields.Date.today)

    @api.constrains('sale_order_id', 'account_move_id')
    def _check_parent_document(self):
        for guarantee in self:
            if bool(guarantee.sale_order_id) == bool(guarantee.account_move_id):
                raise ValidationError(
                    _('A guarantee must be linked to either a sale order or an invoice, not both or neither.')
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('customer_id') and not vals.get('sale_order_customer_guarantees_status'):
                partner = self.env['res.partner'].browse(vals['customer_id'])
                vals['sale_order_customer_guarantees_status'] = partner.status or 'active'
        records = super().create(vals_list)
        records._sync_parent_guarantees_many2many()
        return records

    def write(self, vals):
        result = super().write(vals)
        if {'customer_id', 'sale_order_id', 'account_move_id'} & set(vals):
            self._sync_parent_guarantees_many2many()
        return result

    def unlink(self):
        parents = self.mapped('sale_order_id') | self.mapped('account_move_id')
        result = super().unlink()
        parents._sync_guarantees_many2many_from_list()
        return result

    def _sync_parent_guarantees_many2many(self):
        self.mapped('sale_order_id')._sync_guarantees_many2many_from_list()
        self.mapped('account_move_id')._sync_guarantees_many2many_from_list()

    @api.onchange('customer_id')
    def _onchange_customer_id(self):
        if self.customer_id:
            self.sale_order_customer_guarantees_status = self.customer_id.status or 'active'
