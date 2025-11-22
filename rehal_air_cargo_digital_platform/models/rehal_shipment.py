# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

from .rehal_flight import KSA_CITIES

class RehalShipment(models.Model):
    _name = 'rehal.shipment'
    _description = 'Shipment/Booking'
    _order = 'booking_date desc'

    name = fields.Char(string='Shipment Number', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    flight_id = fields.Many2one('rehal.flight', string='Flight', required=True, ondelete='restrict')
    spot_id = fields.Many2one('rehal.spot', string='Spot', domain="[('flight_id', '=', flight_id), ('state', 'in', ['available', 'booked'])]")
    booking_date = fields.Datetime(string='Booking Date', required=True, default=fields.Datetime.now)
    shipper_name = fields.Char(string='Shipper Name', required=True)
    shipper_phone = fields.Char(string='Shipper Phone')
    shipper_email = fields.Char(string='Shipper Email')
    consignee_name = fields.Char(string='Consignee Name', required=True)
    consignee_phone = fields.Char(string='Consignee Phone')
    consignee_email = fields.Char(string='Consignee Email')
    origin_address = fields.Selection(KSA_CITIES, string='Origin City')
    destination_address = fields.Selection(KSA_CITIES, string='Destination City')
    
    # Shipment details
    description = fields.Text(string='Description')
    weight = fields.Float(string='Weight (kg)', required=True, default=0.0)
    volume = fields.Float(string='Volume (m³)', default=0.0)
    pieces = fields.Integer(string='Number of Pieces', default=1)
    declared_value = fields.Monetary(string='Declared Value', currency_field='currency_id')
    
    # Pricing
    base_rate = fields.Monetary(string='Base Rate', currency_field='currency_id', compute='_compute_pricing', store=True)
    weight_rate = fields.Monetary(string='Weight Rate', currency_field='currency_id', compute='_compute_pricing', store=True)
    fuel_surcharge = fields.Monetary(string='Fuel Surcharge', currency_field='currency_id', compute='_compute_pricing', store=True)
    total_cost = fields.Monetary(string='Total Cost', currency_field='currency_id', compute='_compute_pricing', store=True)
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True)
    
    # Additional fields
    notes = fields.Text(string='Internal Notes')
    tracking_number = fields.Char(string='Tracking Number', copy=False)
    delivery_date = fields.Datetime(string='Delivery Date')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer')
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')

    @api.depends('weight', 'volume', 'declared_value', 'flight_id')
    def _compute_pricing(self):
        for record in self:
            # Base rate calculation (can be customized)
            base_rate = 50.0  # Default base rate
            weight_rate = record.weight * 2.0  # 2 currency units per kg
            fuel_surcharge = (base_rate + weight_rate) * 0.15  # 15% fuel surcharge
            
            record.base_rate = base_rate
            record.weight_rate = weight_rate
            record.fuel_surcharge = fuel_surcharge
            record.total_cost = base_rate + weight_rate + fuel_surcharge

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('rehal.shipment') or _('New')
        
        shipment = super(RehalShipment, self).create(vals)
        
        # Validate booking time
        if shipment.flight_id:
            shipment._validate_booking_time()
        
        # Update spot capacity
        if shipment.spot_id:
            shipment._update_spot_capacity()
        
        return shipment

    def write(self, vals):
        result = super(RehalShipment, self).write(vals)
        
        # Validate booking time if flight or state changed
        if 'flight_id' in vals or 'state' in vals:
            for shipment in self:
                if shipment.flight_id and shipment.state == 'confirmed':
                    shipment._validate_booking_time()
        
        # Update spot capacity if weight or spot changed
        if 'weight' in vals or 'spot_id' in vals:
            for shipment in self:
                shipment._update_spot_capacity()
        
        return result

    def _validate_booking_time(self):
        """Validate that booking is made at least 2 hours before flight departure"""
        for record in self:
            if not record.flight_id or not record.flight_id.departure_datetime:
                continue
            
            if record.state == 'confirmed':
                now = fields.Datetime.now()
                booking_deadline = record.flight_id.departure_datetime - timedelta(hours=2)
                
                if now >= booking_deadline:
                    raise UserError(_(
                        'Cannot confirm booking. Flight departs in less than 2 hours.\n'
                        'Flight: %s\n'
                        'Departure: %s\n'
                        'Booking deadline: %s'
                    ) % (
                        record.flight_id.name,
                        record.flight_id.departure_datetime,
                        booking_deadline
                    ))

    def _update_spot_capacity(self):
        """Update spot capacity when shipment weight changes"""
        for record in self:
            if record.spot_id:
                # Trigger the compute method on the spot
                record.spot_id._update_capacity_used()

    def action_confirm(self):
        self._validate_booking_time()
        self.write({'state': 'confirmed'})
        if self.spot_id:
            self._update_spot_capacity()
        # Generate tracking number
        if not self.tracking_number:
            self.tracking_number = self.env['ir.sequence'].next_by_code('rehal.shipment.tracking') or self.name

    def action_in_transit(self):
        self.write({'state': 'in_transit'})
        if self.flight_id:
            self.flight_id.action_in_transit()

    def action_deliver(self):
        self.write({
            'state': 'delivered',
            'delivery_date': fields.Datetime.now()
        })

    def action_cancel(self):
        self.write({'state': 'cancelled'})
        if self.spot_id:
            self._update_spot_capacity()

    @api.constrains('weight')
    def _check_weight(self):
        for record in self:
            if record.weight <= 0:
                raise ValidationError(_('Weight must be greater than 0.'))

    @api.constrains('spot_id', 'weight')
    def _check_spot_capacity(self):
        for record in self:
            if record.spot_id and record.state in ('confirmed', 'in_transit'):
                available = record.spot_id.capacity_available
                if record.weight > available:
                    raise ValidationError(_(
                        'Weight exceeds available capacity in the selected spot.\n'
                        'Available: %s kg\n'
                        'Requested: %s kg'
                    ) % (available, record.weight))
