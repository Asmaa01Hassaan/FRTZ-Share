# -*- coding: utf-8 -*-

from odoo import http, fields, _
from odoo.http import request
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

from odoo.addons.rehal_air_cargo_digital_platform.models.rehal_flight import KSA_CITIES

class RehalPublicController(http.Controller):

    @http.route(['/rehal/flights', '/rehal/flights/page/<int:page>'], type='http', auth='public', website=True)
    def flights_list(self, page=1, search='', **kw):
        """Display list of available flights"""
        Flight = request.env['rehal.flight']
        
        domain = [
            ('state', 'in', ('draft', 'scheduled')),
            ('can_book', '=', True)
        ]
        
        if search:
            domain.append('|')
            domain.append(('name', 'ilike', search))
            domain.append(('flight_code', 'ilike', search))
        
        flights = Flight.search(domain, order='departure_date, departure_time')
        
        # Pagination
        pager = request.website.pager(
            url='/rehal/flights',
            url_args={'search': search},
            total=len(flights),
            page=page,
            step=10
        )
        
        flights_page = flights[(page - 1) * 10:page * 10]
        
        values = {
            'flights': flights_page,
            'pager': pager,
            'search': search,
        }
        
        return request.render('rehal_air_cargo_digital_platform.flights_list_template', values)

    @http.route(['/rehal/flight/<int:flight_id>'], type='http', auth='public', website=True)
    def flight_details(self, flight_id, **kw):
        """Display flight details with spots"""
        flight = request.env['rehal.flight'].browse(flight_id)
        
        if not flight.exists() or flight.state not in ('draft', 'scheduled'):
            return request.redirect('/rehal/flights')
        
        # Check if booking is still allowed (2 hours before departure)
        now = datetime.now()
        if flight.departure_datetime:
            departure_dt = flight.departure_datetime
            booking_deadline = departure_dt - timedelta(hours=2)
            can_book = now < booking_deadline
        else:
            can_book = False
            booking_deadline = None
        
        values = {
            'flight': flight,
            'can_book': can_book,
            'booking_deadline': booking_deadline,
        }
        
        return request.render('rehal_air_cargo_digital_platform.flight_details_template', values)

    @http.route(['/rehal/flight/<int:flight_id>/book'], type='http', auth='public', website=True)
    def flight_book(self, flight_id, **kw):
        """Display booking form"""
        flight = request.env['rehal.flight'].browse(flight_id)
        
        if not flight.exists() or flight.state not in ('draft', 'scheduled'):
            return request.redirect('/rehal/flights')
        
        # Check if booking is still allowed
        now = fields.Datetime.now()
        booking_deadline = flight.departure_datetime - timedelta(hours=2)
        if now >= booking_deadline:
            return request.redirect(f'/rehal/flight/{flight_id}?error=deadline_passed')
        
        # Get available spots
        available_spots = flight.spot_ids.filtered(
            lambda s: s.state in ('available', 'booked') and s.capacity_available > 0
        )
        
        values = {
            'flight': flight,
            'available_spots': available_spots,
            'ksa_cities': sorted([city[0] for city in KSA_CITIES]),
        }
        
        return request.render('rehal_air_cargo_digital_platform.booking_form_template', values)

    @http.route(['/rehal/flight/<int:flight_id>/book/submit'], type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def flight_book_submit(self, flight_id, **post):
        """Process booking submission"""
        flight = request.env['rehal.flight'].browse(flight_id)
        
        if not flight.exists() or flight.state not in ('draft', 'scheduled'):
            return request.redirect('/rehal/flights')
        
        # Check if booking is still allowed
        now = datetime.now()
        if not flight.departure_datetime:
            return request.redirect(f'/rehal/flight/{flight_id}?error=no_departure_time')
        departure_dt = flight.departure_datetime
        booking_deadline = departure_dt - timedelta(hours=2)
        if now >= booking_deadline:
            return request.redirect(f'/rehal/flight/{flight_id}?error=deadline_passed')
        
        try:
            # Validate required fields
            required_fields = ['shipper_name', 'consignee_name', 'weight', 'spot_id']
            for field in required_fields:
                if not post.get(field):
                    raise ValidationError(_(f'Field {field} is required.'))
            
            # Get spot and validate capacity
            spot = request.env['rehal.spot'].browse(int(post.get('spot_id')))
            weight = float(post.get('weight', 0))
            
            if weight <= 0:
                raise ValidationError(_('Weight must be greater than 0.'))
            
            if weight > spot.capacity_available:
                raise ValidationError(_(
                    'Weight exceeds available capacity in the selected spot.\n'
                    'Available: %s kg\n'
                    'Requested: %s kg'
                ) % (spot.capacity_available, weight))
            
            # Create shipment
            shipment_vals = {
                'flight_id': flight_id,
                'spot_id': int(post.get('spot_id')),
                'shipper_name': post.get('shipper_name'),
                'shipper_phone': post.get('shipper_phone', ''),
                'shipper_email': post.get('shipper_email', ''),
                'consignee_name': post.get('consignee_name'),
                'consignee_phone': post.get('consignee_phone', ''),
                'consignee_email': post.get('consignee_email', ''),
                'origin_address': post.get('origin_address', ''),
                'destination_address': post.get('destination_address', ''),
                'description': post.get('description', ''),
                'weight': weight,
                'volume': float(post.get('volume', 0)),
                'pieces': int(post.get('pieces', 1)),
                'state': 'draft',
            }
            
            shipment = request.env['rehal.shipment'].sudo().create(shipment_vals)
            
            # Shipment remains in draft state
            
            return request.redirect(f'/rehal/booking/confirmation/{shipment.id}')
            
        except (ValidationError, UserError) as e:
            return request.redirect(f'/rehal/flight/{flight_id}/book?error={str(e)}')
        except Exception as e:
            return request.redirect(f'/rehal/flight/{flight_id}/book?error=unknown_error')

    @http.route(['/rehal/booking/confirmation/<int:shipment_id>'], type='http', auth='public', website=True)
    def booking_confirmation(self, shipment_id, **kw):
        """Display booking confirmation"""
        shipment = request.env['rehal.shipment'].browse(shipment_id)
        
        if not shipment.exists():
            return request.redirect('/rehal/flights')
        
        values = {
            'shipment': shipment,
        }
        
        return request.render('rehal_air_cargo_digital_platform.booking_confirmation_template', values)

