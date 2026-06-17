# -*- coding: utf-8 -*-
from odoo import models
import logging

_logger = logging.getLogger(__name__)

class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    def _get_configured_expression_fields(self):
        """Return {(model_name, field_name), ...} for all custom expression variables."""
        configured = set()
        for item in self.item_ids.filtered(lambda i: i.compute_price == 'expression'):
            for var in item.expression_variable_ids:
                if var.model_id and var.field_id:
                    configured.add((var.model_id.model, var.field_id.name))
        return configured

    def _get_sale_order_installment(self, sale_line=None, sale_order=None):
        """First installment preview for the line (per-lines) or order (per-invoice)."""
        if 'sale.order.installment' not in self.env:
            return self.env['sale.order.installment']
        Installment = self.env['sale.order.installment']
        order = sale_order or (sale_line.order_id if sale_line else False)
        if sale_line:
            line_id = sale_line._origin.id or (
                sale_line.id if isinstance(sale_line.id, int) else False
            )
            if line_id:
                installment = Installment.search(
                    [('sale_order_line_id', '=', line_id)],
                    order='sequence',
                    limit=1,
                )
                if installment:
                    return installment
            if order and hasattr(order, 'installment_preview_ids'):
                preview = order.installment_preview_ids.filtered(
                    lambda inst: inst.sale_order_line_id == sale_line
                ).sorted('sequence')
                if preview:
                    return preview[0]
        if order:
            order_id = order._origin.id or (
                order.id if isinstance(order.id, int) else False
            )
            if order_id:
                installment = Installment.search(
                    [
                        ('sale_order_id', '=', order_id),
                        ('sale_order_line_id', '=', False),
                    ],
                    order='sequence',
                    limit=1,
                )
                if installment:
                    return installment
            if hasattr(order, 'installment_preview_ids'):
                preview = order.installment_preview_ids.filtered(
                    lambda inst: not inst.sale_order_line_id
                ).sorted('sequence')
                if preview:
                    return preview[0]
        return Installment

    def _get_account_move_installment(self, move_line=None, move=None):
        """First invoice installment for the line (per-lines) or invoice (per-invoice)."""
        if 'account.move.installment' not in self.env:
            return self.env['account.move.installment']
        Installment = self.env['account.move.installment']
        invoice = move or (move_line.move_id if move_line else False)
        if move_line:
            line_id = move_line._origin.id or (
                move_line.id if isinstance(move_line.id, int) else False
            )
            if line_id:
                installment = Installment.search(
                    [('invoice_line_id', '=', line_id)],
                    order='sequence',
                    limit=1,
                )
                if installment:
                    return installment
            if invoice and hasattr(invoice, 'installment_ids'):
                preview = invoice.installment_ids.filtered(
                    lambda inst: inst.invoice_line_id == move_line
                ).sorted('sequence')
                if preview:
                    return preview[0]
        if invoice:
            move_id = invoice._origin.id or (
                invoice.id if isinstance(invoice.id, int) else False
            )
            if move_id:
                installment = Installment.search(
                    [
                        ('move_id', '=', move_id),
                        ('invoice_line_id', '=', False),
                    ],
                    order='sequence',
                    limit=1,
                )
                if installment:
                    return installment
            if hasattr(invoice, 'installment_ids'):
                preview = invoice.installment_ids.filtered(
                    lambda inst: not inst.invoice_line_id
                ).sorted('sequence')
                if preview:
                    return preview[0]
        return Installment

    def _build_expression_sources(self, sale_line=None, sale_order=None, product=None, move_line=None, move=None):
        """Build serializable field-value maps for expression variable resolution."""
        configured = self._get_configured_expression_fields()
        if not configured:
            return {}

        needed_models = {model_name for model_name, _field_name in configured}
        record_map = {
            'sale.order.line': sale_line,
            'sale.order': sale_order or (sale_line.order_id if sale_line else False),
            'product.product': product or (sale_line.product_id if sale_line else (move_line.product_id if move_line else False)),
            'account.move.line': move_line,
            'account.move': move or (move_line.move_id if move_line else False),
        }
        if 'sale.order.installment' in needed_models:
            record_map['sale.order.installment'] = self._get_sale_order_installment(
                sale_line=sale_line,
                sale_order=record_map['sale.order'],
            )
        if 'account.move.installment' in needed_models:
            record_map['account.move.installment'] = self._get_account_move_installment(
                move_line=move_line,
                move=record_map['account.move'],
            )

        sources = {}
        for model_name, field_name in configured:
            record = record_map.get(model_name)
            if not record:
                continue
            try:
                value = record[field_name]
            except KeyError:
                continue
            sources.setdefault(model_name, {})[field_name] = value
        return sources

    def _compute_price_rule(
        self, products, quantity, currency=None, uom=None, date=False, compute_price=True, **kwargs
    ):
        """Enhanced price rule computation with installment support"""
        res = super()._compute_price_rule(
            products,
            quantity,
            currency=currency,
            uom=uom,
            date=date,
            compute_price=compute_price,
            **kwargs
        )

        # Skip if only rule selection is requested (not price computation)
        if compute_price is False:
            return res

        # Log installment context for debugging
        installment_num = float(self._context.get('installment_num', 0.0) or 0.0)
        payment_type = self._context.get('payment_type')
        if installment_num > 0 or payment_type:
            _logger.debug(f"Computing prices with context: installment_num={installment_num}, payment_type={payment_type}")

        return res

    def _get_applicable_rules_domain(self, products, date, **kwargs):
        """Keep rule lookup broad; payment-plan filtering is applied after lookup."""
        domain = super()._get_applicable_rules_domain(products=products, date=date, **kwargs)
        return domain

    def _get_applicable_rules(self, products, date, **kwargs):
        """Override to filter by payment_type after getting rules"""
        rules = super()._get_applicable_rules(products=products, date=date, **kwargs)
        
        # Additional filtering as safety measure (domain should handle it, but this ensures correctness)
        payment_type = self._context.get('payment_type')
        if payment_type:
            # Prefer rules that are generic or explicitly match the payment plan.
            filtered_rules = rules.filtered(
                lambda r: not r.payment_type or r.payment_type == payment_type
            )
            if filtered_rules:
                if len(filtered_rules) != len(rules):
                    _logger.debug(f"Filtered {len(rules)} rules to {len(filtered_rules)} by payment_type={payment_type}")
                return filtered_rules
            if rules:
                _logger.debug(f"Filtered {len(rules)} rules to {len(filtered_rules)} by payment_type={payment_type}")
                _logger.debug("No matching payment-plan rules found; falling back to regular pricelist rule order")
        
        return rules
