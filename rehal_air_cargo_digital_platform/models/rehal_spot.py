# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class RehalSpot(models.Model):
    _name = 'rehal.spot'
    _description = 'Flight Spot'
    _order = 'name'

    name = fields.Char(string='Spot Name', required=True)
    flight_id = fields.Many2one('rehal.flight', string='Flight', required=True, ondelete='cascade')
    state = fields.Selection([
        ('available', 'Available'),
        ('booked', 'Booked'),
        ('full', 'Full'),
    ], string='Status', default='available', required=True)
    capacity = fields.Float(string='Total Capacity (kg)', required=True, default=100.0)
    capacity_used = fields.Float(string='Used Capacity (kg)', default=0.0, compute='_update_capacity_used', store=True)
    capacity_available = fields.Float(string='Available Capacity (kg)', compute='_compute_capacity_available', store=True)
    utilization_percent = fields.Float(string='Utilization %', compute='_compute_utilization', store=True)
    shipment_ids = fields.One2many('rehal.shipment', 'spot_id', string='Shipments')
    color = fields.Integer(string='Color Index', compute='_compute_color')
    
    # Display fields
    status_display = fields.Char(string='Status Display', compute='_compute_status_display')
    spot_color_class = fields.Char(string='Color Class', compute='_compute_color_class')

    @api.depends('capacity_used', 'capacity')
    def _compute_capacity_available(self):
        for record in self:
            record.capacity_available = max(0, record.capacity - record.capacity_used)

    @api.depends('capacity_used', 'capacity')
    def _compute_utilization(self):
        for record in self:
            if record.capacity > 0:
                record.utilization_percent = (record.capacity_used / record.capacity) * 100
            else:
                record.utilization_percent = 0

    @api.depends('state', 'capacity_used', 'capacity')
    def _compute_color(self):
        for record in self:
            if record.state == 'full' or (record.capacity_used >= record.capacity and record.capacity > 0):
                record.color = 1  # Red
            elif record.state == 'booked' and record.capacity_used > 0:
                record.color = 2  # Orange
            else:
                record.color = 10  # Green

    @api.depends('state', 'capacity_used', 'capacity')
    def _compute_status_display(self):
        for record in self:
            if record.state == 'full' or (record.capacity_used >= record.capacity and record.capacity > 0):
                record.status_display = 'Full'
            elif record.state == 'booked' and record.capacity_used > 0:
                record.status_display = f'Partial ({record.utilization_percent:.0f}%)'
            else:
                record.status_display = 'Empty'

    @api.depends('state', 'capacity_used', 'capacity')
    def _compute_color_class(self):
        for record in self:
            if record.state == 'full' or (record.capacity_used >= record.capacity and record.capacity > 0):
                record.spot_color_class = 'spot-full'
            elif record.state == 'booked' and record.capacity_used > 0:
                record.spot_color_class = 'spot-partial'
            else:
                record.spot_color_class = 'spot-empty'

    @api.depends('shipment_ids', 'shipment_ids.weight', 'shipment_ids.state')
    def _update_capacity_used(self):
        for record in self:
            # Only count confirmed or in-transit shipments
            active_shipments = record.shipment_ids.filtered(
                lambda s: s.state in ('confirmed', 'in_transit')
            )
            total_weight = sum(active_shipments.mapped('weight'))
            record.capacity_used = total_weight
            if record.capacity_used >= record.capacity:
                record.state = 'full'
            elif record.capacity_used > 0:
                record.state = 'booked'
            else:
                record.state = 'available'

    def action_mark_full(self):
        self.write({'state': 'full', 'capacity_used': self.capacity})

    def action_mark_available(self):
        self.write({'state': 'available', 'capacity_used': 0.0})

    @api.constrains('capacity_used', 'capacity')
    def _check_capacity(self):
        for record in self:
            if record.capacity_used > record.capacity:
                raise ValidationError(_('Used capacity cannot exceed total capacity.'))

