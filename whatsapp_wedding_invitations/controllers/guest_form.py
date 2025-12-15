# -*- coding: utf-8 -*-

import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class GuestFormController(http.Controller):
    """Controller for adding guests via website form"""
    
    @http.route('/event/add-guest', type='http', auth='public', website=True, csrf=True)
    def guest_form(self, **kwargs):
        """Display guest form and handle submission"""
        
        # Get all calendar events for dropdown
        events = request.env['calendar.event'].sudo().search([
            ('active', '=', True)
        ], order='start desc', limit=100)
        
        # If POST request, process the form
        if request.httprequest.method == 'POST':
            try:
                # Get form data
                name = kwargs.get('name', '').strip()
                phone_number = kwargs.get('phone_number', '').strip()
                email = kwargs.get('email', '').strip()
                calendar_event_id = kwargs.get('calendar_event_id', '')
                
                # Validation
                errors = {}
                if not name:
                    errors['name'] = 'الاسم مطلوب'
                if not phone_number:
                    errors['phone_number'] = 'رقم الهاتف مطلوب'
                if not calendar_event_id:
                    errors['calendar_event_id'] = 'الحدث مطلوب'
                
                if errors:
                    return request.render('whatsapp_wedding_invitations.guest_form_template', {
                        'events': events,
                        'errors': errors,
                        'form_data': kwargs
                    })
                
                # Create guest
                guest_vals = {
                    'name': name,
                    'phone_number': phone_number,
                    'calendar_event_id': int(calendar_event_id),
                    'rsvp_status': 'pending',
                }
                
                if email:
                    guest_vals['email'] = email
                
                guest = request.env['event.guest'].sudo().create(guest_vals)
                
                _logger.info(f'Guest {guest.name} added via website form for event {guest.calendar_event_id.name}')
                
                return request.render('whatsapp_wedding_invitations.guest_form_success', {
                    'guest': guest,
                    'event': guest.calendar_event_id
                })
                
            except Exception as e:
                _logger.error(f'Error creating guest: {str(e)}', exc_info=True)
                return request.render('whatsapp_wedding_invitations.guest_form_template', {
                    'events': events,
                    'errors': {'general': f'حدث خطأ: {str(e)}'},
                    'form_data': kwargs
                })
        
        # GET request - show form
        return request.render('whatsapp_wedding_invitations.guest_form_template', {
            'events': events,
            'errors': {},
            'form_data': {}
        })

