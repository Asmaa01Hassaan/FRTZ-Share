# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    subscription_ids = fields.One2many(
        'sale.order', 'partner_id', string='Subscriptions',
        domain=[('is_subscription', '=', True)])
    subscription_count = fields.Integer(
        compute='_compute_subscription_stats', string='Subscriptions')
    subscription_active_count = fields.Integer(
        compute='_compute_subscription_stats', string='Active Subscriptions')
    subscription_mrr = fields.Monetary(
        compute='_compute_subscription_stats', string='Subscriptions MRR',
        currency_field='currency_id')
    subscription_next_invoice_date = fields.Date(
        compute='_compute_subscription_stats', string='Next Subscription Invoice')
    subscription_overdue_count = fields.Integer(
        compute='_compute_subscription_stats', string='Overdue Subscriptions')

    @api.depends('subscription_ids.subscription_state',
                 'subscription_ids.subscription_mrr',
                 'subscription_ids.subscription_next_invoice_date',
                 'subscription_ids.subscription_is_overdue')
    def _compute_subscription_stats(self):
        for partner in self:
            subs = partner.subscription_ids
            active = subs.filtered(lambda o: o.subscription_state == 'active')
            partner.subscription_count = len(subs)
            partner.subscription_active_count = len(active)
            partner.subscription_mrr = sum(active.mapped('subscription_mrr'))
            dates = [d for d in active.mapped('subscription_next_invoice_date') if d]
            partner.subscription_next_invoice_date = min(dates) if dates else False
            partner.subscription_overdue_count = len(
                active.filtered(lambda o: o.subscription_is_overdue))

    def action_view_partner_subscriptions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Subscriptions'),
            'res_model': 'sale.order',
            'domain': [('is_subscription', '=', True), ('partner_id', '=', self.id)],
            'view_mode': 'kanban,list,form',
            'context': {'create': False, 'search_default_group_by_state': 1},
        }
