# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools.misc import str2bool


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _default_invoice_pricelist_id(self):
        if not self._is_invoice_pricelist_enabled():
            return False
        return self.env.user.partner_id.property_product_pricelist

    invoice_pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Pricelist',
        default=_default_invoice_pricelist_id,
        check_company=True,
        copy=False,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help='Pricelist used to compute product prices on invoice lines.',
    )
    show_invoice_pricelist = fields.Boolean(
        compute='_compute_show_invoice_pricelist',
        store=False,
    )

    @api.depends_context('company')
    def _compute_show_invoice_pricelist(self):
        enabled = self._is_invoice_pricelist_enabled()
        for move in self:
            move.show_invoice_pricelist = enabled

    def _is_invoice_pricelist_enabled(self):
        value = self.env['ir.config_parameter'].sudo().get_param(
            'pricelist_expression.show_invoice_pricelist',
            default=False,
        )
        if value is False:
            value = self.env['ir.config_parameter'].sudo().get_param(
                'payment_term_installment_extension.show_invoice_pricelist',
                default='False',
            )
        return str2bool(value, default=False)

    def _should_apply_invoice_pricelist(self):
        self.ensure_one()
        return (
            self._is_invoice_pricelist_enabled()
            and self.is_sale_document(include_receipts=True)
            and bool(self.invoice_pricelist_id)
        )

    def _get_invoice_pricelist_lines(self):
        return self.line_ids.filtered(
            lambda line: line.product_id and line.display_type in (False, 'product')
        )

    def _get_invoice_pricelist_context(self, line=False):
        self.ensure_one()
        ctx = dict(self.env.context or {})
        ctx['payment_type'] = getattr(self, 'payment_type', False)
        if (
            (getattr(self, 'scope', False) == 'per_lines' or getattr(self, 'apply_payment_term_per_line', False))
            and line
        ):
            ctx['installment_num'] = float(getattr(line, 'line_installment_count', 0.0) or 0.0)
            ctx['first_payment'] = float(getattr(line, 'line_first_payment_percentage', 0.0) or 0.0)
        else:
            ctx['installment_num'] = float(getattr(self, 'installment_count', 0.0) or 0.0)
            ctx['first_payment'] = float(getattr(self, 'first_payment_percentage', 0.0) or 0.0)
        if self.invoice_pricelist_id:
            ctx['pricelist_expression_sources'] = self.invoice_pricelist_id._build_expression_sources(
                move_line=line,
                move=self,
                product=line.product_id if line else False,
            )
        return ctx

    def _get_invoice_pricelist_price(self, line):
        self.ensure_one()
        quantity = line.quantity or 1.0
        uom = line.product_uom_id or line.product_id.uom_id
        date = self.invoice_date or self.date or fields.Date.context_today(self)
        return self.invoice_pricelist_id.with_context(
            self._get_invoice_pricelist_context(line)
        )._get_product_price(
            line.product_id,
            quantity,
            uom=uom,
            date=date,
            currency=self.currency_id,
        )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'show_invoice_pricelist' in fields_list:
            res['show_invoice_pricelist'] = self._is_invoice_pricelist_enabled()
        return res

    @api.onchange('partner_id', 'company_id')
    def _onchange_invoice_pricelist_partner_id(self):
        for move in self.filtered(lambda item: item._is_invoice_pricelist_enabled() and item.is_sale_document(include_receipts=True)):
            move.invoice_pricelist_id = move.partner_id.property_product_pricelist

    @api.onchange('invoice_pricelist_id')
    def _onchange_invoice_pricelist_id(self):
        for move in self.filtered(lambda item: item.invoice_pricelist_id):
            if move.invoice_pricelist_id.currency_id:
                move.currency_id = move.invoice_pricelist_id.currency_id
            move.invoice_line_ids._recompute_price_from_invoice_pricelist()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            move_type = vals.get('move_type') or self.env.context.get('default_move_type')
            if (
                self._is_invoice_pricelist_enabled()
                and move_type in ('out_invoice', 'out_refund', 'out_receipt')
                and vals.get('partner_id')
                and not vals.get('invoice_pricelist_id')
            ):
                partner = self.env['res.partner'].browse(vals['partner_id'])
                if partner.property_product_pricelist:
                    vals['invoice_pricelist_id'] = partner.property_product_pricelist.id
                    vals.setdefault('currency_id', partner.property_product_pricelist.currency_id.id)
        moves = super().create(vals_list)
        moves_to_reprice = moves.filtered(lambda item: item.state == 'draft' and item._should_apply_invoice_pricelist())
        if moves_to_reprice:
            self.env.flush_all()
            for move in moves_to_reprice:
                lines = move._get_invoice_pricelist_lines().filtered(lambda line: not line.sale_line_ids)
                if lines:
                    lines._recompute_price_from_invoice_pricelist()
        return moves

    def write(self, vals):
        result = super().write(vals)
        if any(field in vals for field in (
            'invoice_pricelist_id',
            'payment_type',
            'scope',
            'apply_payment_term_per_line',
            'installment_count',
            'first_payment_percentage',
            'first_payment_type',
        )):
            for move in self.filtered(lambda item: item.state == 'draft' and item._should_apply_invoice_pricelist()):
                move._get_invoice_pricelist_lines()._recompute_price_from_invoice_pricelist()
        return result


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_linked_sale_order_price_unit(self):
        """Return SO line unit price when this invoice line comes from a sales order."""
        self.ensure_one()
        sale_line = self.sale_line_ids[:1]
        if sale_line:
            return sale_line.price_unit
        return None

    def _set_invoice_line_price_unit(self, price):
        self.ensure_one()
        if self.id and self.move_id.id:
            self.with_context(skip_invoice_pricelist_price=True).write({
                'price_unit': price,
            })
        else:
            self.price_unit = price

    def _recompute_price_from_invoice_pricelist(self):
        """Update line unit price from invoice pricelist.

        During UI onchange the parent move may not be persisted yet; assign
        price_unit in memory instead of write() to avoid unbalanced-move SQL.
        Lines created from sales orders keep the sale order line unit price.
        """
        for line in self.filtered(lambda item: item.product_id and item.move_id):
            linked_price = line._get_linked_sale_order_price_unit()
            if linked_price is not None:
                line._set_invoice_line_price_unit(linked_price)
                continue
            if not line.move_id._should_apply_invoice_pricelist():
                continue
            price = line.move_id._get_invoice_pricelist_price(line)
            line._set_invoice_line_price_unit(price)

    @api.depends(
        'product_id',
        'product_uom_id',
        'quantity',
        'move_id.invoice_pricelist_id',
        'move_id.invoice_date',
        'move_id.date',
        'move_id.payment_type',
        'move_id.scope',
        'move_id.apply_payment_term_per_line',
        'move_id.installment_count',
        'move_id.first_payment_percentage',
        'move_id.first_payment_type',
        'line_installment_count',
        'line_first_payment_type',
        'line_first_payment_percentage',
    )
    def _compute_price_unit(self):
        super()._compute_price_unit()
        if self.env.context.get('skip_invoice_pricelist_price'):
            return
        for line in self.filtered(lambda item: item.product_id and item.move_id):
            linked_price = line._get_linked_sale_order_price_unit()
            if linked_price is not None:
                line.price_unit = linked_price
                continue
            if line.move_id._should_apply_invoice_pricelist():
                line.price_unit = line.move_id._get_invoice_pricelist_price(line)
