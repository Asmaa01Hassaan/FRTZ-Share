# -*- coding: utf-8 -*-
from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)

_LINE_INSTALLMENT_FIELDS = (
    'line_installment_count',
    'line_first_payment_type',
    'line_first_payment_percentage',
)
_ORDER_INSTALLMENT_FIELDS = (
    'payment_type',
    'scope',
    'apply_payment_term_per_line',
    'installment_count',
    'first_payment_percentage',
    'first_payment_type',
)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_immediate_term = fields.Boolean(
        related='order_id.is_immediate_term',
        store=False,
        readonly=True,
    )

    def _get_pricelist_context(self):
        """Build pricing context aligned with invoice pricelist logic."""
        ctx = dict(self.env.context or {})
        order = self.order_id
        if order and hasattr(order, '_get_pricelist_context'):
            try:
                ctx.update(order._get_pricelist_context())
            except Exception as exc:
                _logger.warning('Error getting pricelist context from order: %s', exc)

        if order and hasattr(order, 'payment_type'):
            ctx['payment_type'] = order.payment_type

        per_lines = bool(getattr(order, 'apply_payment_term_per_line', False))
        if per_lines:
            ctx['installment_num'] = float(self.line_installment_count or 0.0)
            ctx['first_payment'] = float(self.line_first_payment_percentage or 0.0)
        elif order:
            ctx['installment_num'] = float(order.installment_count or 0.0)
            ctx['first_payment'] = float(order.first_payment_percentage or 0.0)
        else:
            ctx['installment_num'] = 0.0
            ctx['first_payment'] = 0.0

        pricelist = order.pricelist_id if order else False
        if pricelist:
            ctx['pricelist_expression_sources'] = pricelist._build_expression_sources(
                sale_line=self,
                sale_order=order,
                product=self.product_id,
            )

        _logger.debug(
            'Pricelist context: line_id=%s, payment_type=%s, installment_num=%s, first_payment=%s',
            self.id or 'new',
            ctx.get('payment_type'),
            ctx['installment_num'],
            ctx['first_payment'],
        )
        return ctx

    def _refresh_installment_preview(self):
        if (
            self.env.context.get('skip_auto_generate_sale_payment_term')
            or self.env.context.get('regenerating_installment_preview')
            or self.env.context.get('syncing_order_lines_from_payment_terms')
        ):
            return
        orders = self.mapped('order_id')
        if orders and hasattr(orders, '_regenerate_installment_preview'):
            orders._regenerate_installment_preview()

    def _recompute_price_from_installments(self):
        if self.env.context.get('skip_recompute_price_from_installments'):
            return
        for line in self:
            if not line.product_id or not line.order_id or not line.order_id.pricelist_id:
                continue
            try:
                ctx = line._get_pricelist_context()
                price = super(SaleOrderLine, line.with_context(ctx))._get_pricelist_price()
                line.price_unit = price
            except Exception as exc:
                _logger.error('Error recomputing price for line %s: %s', line.id, exc)
        self._refresh_installment_preview()

    @api.onchange('order_id')
    def _onchange_order_id_pricelist_installments(self):
        if self.order_id and self.order_id.is_immediate_term:
            self.line_installment_count = 0
            self.line_first_payment_percentage = 0.0

    @api.onchange(*_LINE_INSTALLMENT_FIELDS)
    def _onchange_line_installment_pricelist(self):
        if self.order_id and self.order_id.is_immediate_term:
            self.line_installment_count = 0
            self.line_first_payment_percentage = 0.0
        self._recompute_price_from_installments()

    @api.onchange('product_id', 'product_uom', 'product_uom_qty')
    def _onchange_product_or_qty_pricelist(self):
        self._recompute_price_from_installments()

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        if (
            not self.env.context.get('skip_recompute_price_from_installments')
            and any(
                key in vals
                for vals in vals_list
                for key in (*_LINE_INSTALLMENT_FIELDS, 'product_id', 'product_uom', 'product_uom_qty')
            )
        ):
            lines._recompute_price_from_installments()
        return lines

    def write(self, vals):
        res = super().write(vals)
        if (
            not self.env.context.get('skip_recompute_price_from_installments')
            and any(key in vals for key in (*_LINE_INSTALLMENT_FIELDS, 'product_id', 'product_uom', 'product_uom_qty', 'order_id'))
        ):
            self._recompute_price_from_installments()
        return res

    def _get_pricelist_price(self):
        if not self.product_id or not self.order_id or not self.order_id.pricelist_id:
            return self.price_unit or 0.0
        ctx = self._get_pricelist_context()
        return super(SaleOrderLine, self.with_context(ctx))._get_pricelist_price()

    def _prepare_invoice_line(self, **optional_values):
        """Keep sale order line pricing when generating invoice lines."""
        vals = super()._prepare_invoice_line(**optional_values)
        if self.display_type:
            return vals
        vals.update({
            'price_unit': self.price_unit,
            'discount': self.discount,
        })
        return vals


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_immediate_term = fields.Boolean(
        compute='_compute_is_immediate_term',
        store=False,
    )

    @api.depends('payment_type')
    def _compute_is_immediate_term(self):
        for order in self:
            order.is_immediate_term = bool(order.payment_type and order.payment_type == 'immediate')

    def _recompute_order_line_pricelist_prices(self):
        lines = self.order_line.filtered(lambda item: item.product_id)
        for line in lines:
            if not line.order_id.pricelist_id:
                continue
            try:
                ctx = line._get_pricelist_context()
                price = super(SaleOrderLine, line.with_context(ctx))._get_pricelist_price()
                line.price_unit = price
            except Exception as exc:
                _logger.error('Error recomputing price for line %s: %s', line.id, exc)
        if hasattr(self, '_regenerate_installment_preview'):
            self._regenerate_installment_preview()

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        if (
            self.pricelist_id
            and self.env['account.move']._is_invoice_pricelist_enabled()
        ):
            invoice_vals['invoice_pricelist_id'] = self.pricelist_id.id
        return invoice_vals

    @api.onchange('payment_type', 'scope', 'installment_count', 'first_payment_percentage', 'first_payment_type')
    def _onchange_order_installment_pricelist(self):
        for line in self.order_line:
            if self.is_immediate_term:
                line.line_installment_count = 0
                line.line_first_payment_percentage = 0.0
        self._recompute_order_line_pricelist_prices()

    @api.onchange('pricelist_id')
    def _onchange_pricelist_id_installment_preview(self):
        self._recompute_order_line_pricelist_prices()

    def _recompute_prices(self):
        super()._recompute_prices()
        if hasattr(self, '_regenerate_installment_preview'):
            self._regenerate_installment_preview()

    def write(self, vals):
        res = super().write(vals)
        if set(vals) & set(_ORDER_INSTALLMENT_FIELDS):
            for order in self:
                if order.is_immediate_term:
                    order.order_line.write({
                        'line_installment_count': 0,
                        'line_first_payment_percentage': 0.0,
                    })
                order._recompute_order_line_pricelist_prices()
        elif 'pricelist_id' in vals:
            for order in self:
                order._recompute_order_line_pricelist_prices()
        return res
