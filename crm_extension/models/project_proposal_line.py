from odoo import api, fields, models


class ProposalLine(models.Model):
    _name = 'project.proposal.line'
    _description = 'Proposal Line'
    _order = 'id desc'

    proposal_id = fields.Many2one(
        'project.proposal',
        string='Proposal',
        ondelete='cascade'
    )

    product_id = fields.Many2one(
        'product.product',
        string='Product',

    )

    category_id = fields.Many2one(
        related='product_id.categ_id',
        string='Product Category',
        store=True,
        readonly=True
    )

    quantity = fields.Float(string='Quantity', default=1.0)

    price_unit = fields.Float(string='Unit Price')

    tax_ids = fields.Many2many(
        'account.tax',
        string='Taxes',
        domain=[('type_tax_use', 'in', ['sale', 'purchase'])]
    )

    currency_id = fields.Many2one(
        related='proposal_id.currency_id',
        store=True,
        readonly=True
    )

    subtotal = fields.Monetary(
        string='Subtotal',
        compute='_compute_amount',
        store=True
    )

    total = fields.Monetary(
        string='Total',
        compute='_compute_amount',
        store=True
    )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                line.price_unit = line.product_id.lst_price
                line.tax_ids = line.product_id.taxes_id

    @api.depends('quantity', 'price_unit', 'tax_ids')
    def _compute_amount(self):
        for line in self:
            taxes = line.tax_ids.compute_all(
                line.price_unit,
                currency=line.currency_id,
                quantity=line.quantity,
                product=line.product_id,
                partner=line.proposal_id.partner_id
            )
            line.subtotal = taxes['total_excluded']
            line.total = taxes['total_included']
