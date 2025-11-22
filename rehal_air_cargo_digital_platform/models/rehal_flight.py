# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

# KSA Cities List
KSA_CITIES = [
    ('Riyadh', 'Riyadh'), ('Jeddah', 'Jeddah'), ('Mecca', 'Mecca'), 
    ('Medina', 'Medina'), ('Dammam', 'Dammam'), ('Taif', 'Taif'), 
    ('Tabuk', 'Tabuk'), ('Buraydah', 'Buraydah'), ('Khamis Mushait', 'Khamis Mushait'), 
    ('Abha', 'Abha'), ('Al-Khobar', 'Al-Khobar'), ('Jubail', 'Jubail'), 
    ('Hail', 'Hail'), ('Najran', 'Najran'), ('Yanbu', 'Yanbu'), 
    ('Al-Hasa', 'Al-Hasa'), ('Arar', 'Arar'), ('Jizan', 'Jizan'), 
    ('Sakaka', 'Sakaka'), ('Al-Bahah', 'Al-Bahah')
]

class RehalFlight(models.Model):
    _name = 'rehal.flight'
    _description = 'Flight Management'
    _order = 'departure_date, departure_time'

    name = fields.Char(string='Flight Number', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    flight_code = fields.Char(string='Flight Code', required=True)
    origin = fields.Selection(KSA_CITIES, string='Origin', required=True)
    destination = fields.Selection(KSA_CITIES, string='Destination', required=True)
    departure_date = fields.Date(string='Departure Date', required=True)
    departure_time = fields.Float(string='Departure Time', required=True)
    arrival_date = fields.Date(string='Arrival Date', required=True)
    arrival_time = fields.Float(string='Arrival Time', required=True)
    aircraft_type = fields.Char(string='Aircraft Type')
    total_spots = fields.Integer(string='Total Spots', required=True, default=7)
    available_spots = fields.Integer(string='Available Spots', compute='_compute_spot_availability', store=True)
    booked_spots = fields.Integer(string='Booked Spots', compute='_compute_spot_availability', store=True)
    spot_ids = fields.One2many('rehal.spot', 'flight_id', string='Spots')
    shipment_ids = fields.One2many('rehal.shipment', 'flight_id', string='Shipments')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('in_transit', 'In Transit'),
        ('arrived', 'Arrived'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True)
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id', readonly=True)
    
    # Computed fields for display
    departure_datetime = fields.Datetime(string='Departure DateTime', compute='_compute_datetime', store=True)
    arrival_datetime = fields.Datetime(string='Arrival DateTime', compute='_compute_datetime', store=True)
    can_book = fields.Boolean(string='Can Book', compute='_compute_can_book')
    spot_status_summary = fields.Html(string='Spot Status', compute='_compute_spot_status_summary')

    @api.depends('departure_date', 'departure_time')
    def _compute_datetime(self):
        for record in self:
            if record.departure_date and record.departure_time:
                hours = int(record.departure_time)
                minutes = int((record.departure_time - hours) * 60)
                record.departure_datetime = datetime.combine(
                    record.departure_date,
                    datetime.min.time().replace(hour=hours, minute=minutes)
                )
            else:
                record.departure_datetime = False
            
            if record.arrival_date and record.arrival_time:
                hours = int(record.arrival_time)
                minutes = int((record.arrival_time - hours) * 60)
                record.arrival_datetime = datetime.combine(
                    record.arrival_date,
                    datetime.min.time().replace(hour=hours, minute=minutes)
                )
            else:
                record.arrival_datetime = False

    @api.depends('spot_ids', 'spot_ids.state', 'total_spots')
    def _compute_spot_availability(self):
        for record in self:
            # Booked means not available (i.e., 'booked' or 'full')
            booked = len(record.spot_ids.filtered(lambda s: s.state in ['booked', 'full']))
            record.booked_spots = booked
            # Available spots count
            record.available_spots = record.total_spots - booked

    @api.depends('departure_datetime')
    def _compute_can_book(self):
        for record in self:
            if not record.departure_datetime:
                record.can_book = False
                continue
            now = fields.Datetime.now()
            booking_deadline = record.departure_datetime - timedelta(hours=2)
            record.can_book = now < booking_deadline and record.state in ('draft', 'scheduled')

    @api.depends('spot_ids', 'spot_ids.state', 'spot_ids.capacity_used', 'spot_ids.capacity')
    def _compute_spot_status_summary(self):
        for record in self:
            spots = record.spot_ids
            full_spots = spots.filtered(lambda s: s.state == 'booked' and s.capacity_used >= s.capacity)
            partial_spots = spots.filtered(lambda s: s.state == 'booked' and 0 < s.capacity_used < s.capacity)
            empty_spots = spots.filtered(lambda s: s.state == 'available')
            
            html = f"""
            <div style="display: flex; gap: 10px; align-items: center;">
                <span style="background-color: #d32f2f; color: white; padding: 2px 8px; border-radius: 3px;">
                    Full: {len(full_spots)}
                </span>
                <span style="background-color: #ff9800; color: white; padding: 2px 8px; border-radius: 3px;">
                    Partial: {len(partial_spots)}
                </span>
                <span style="background-color: #4caf50; color: white; padding: 2px 8px; border-radius: 3px;">
                    Empty: {len(empty_spots)}
                </span>
            </div>
            """
            record.spot_status_summary = html

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('rehal.flight') or _('New')
        
        # Create spots automatically
        flight = super(RehalFlight, self).create(vals)
        flight._create_spots()
        return flight

    def _create_spots(self):
        """Create spots for the flight based on total_spots"""
        for i in range(1, self.total_spots + 1):
            self.env['rehal.spot'].create({
                'name': f'Spot {i}',
                'flight_id': self.id,
                'state': 'available',
                'capacity': 100.0,  # Default capacity in kg or volume
            })

    def action_schedule(self):
        self.write({'state': 'scheduled'})

    def action_in_transit(self):
        self.write({'state': 'in_transit'})

    def action_arrived(self):
        self.write({'state': 'arrived'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    @api.constrains('departure_date', 'arrival_date', 'departure_time', 'arrival_time')
    def _check_dates(self):
        for record in self:
            if record.departure_date and record.arrival_date:
                if record.arrival_date < record.departure_date:
                    raise ValidationError(_('Arrival date cannot be before departure date.'))
                elif record.arrival_date == record.departure_date:
                    if record.arrival_time <= record.departure_time:
                        raise ValidationError(_('Arrival time must be after departure time.'))

    @api.constrains('total_spots')
    def _check_total_spots(self):
        for record in self:
            if record.total_spots <= 0:
                raise ValidationError(_('Total spots must be greater than 0.'))
