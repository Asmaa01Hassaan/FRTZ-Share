from odoo import api, fields, models, Command


class AccountMove(models.Model):
    _inherit = 'account.move'

    customer_guarantees_ids = fields.Many2many(
        'res.partner',
        'account_move_customer_guarantees_rel',
        'account_move_id',
        'partner_id',
        string='Customer Guarantees',
        help='Select customers who will act as guarantees for this invoice',
    )

    customer_guarantees_list_ids = fields.One2many(
        'customer.guarantees',
        'account_move_id',
        string='Customer Guarantees List',
    )

    guarantees_count = fields.Integer(
        string='Guarantees Count',
        compute='_compute_guarantees_count',
    )

    @api.depends('customer_guarantees_list_ids', 'customer_guarantees_ids')
    def _compute_guarantees_count(self):
        for move in self:
            move.guarantees_count = len(
                move.customer_guarantees_list_ids or move.customer_guarantees_ids
            )

    def _sync_guarantees_many2many_from_list(self):
        for move in self:
            move.customer_guarantees_ids = [
                Command.set(move.customer_guarantees_list_ids.mapped('customer_id').ids)
            ]
