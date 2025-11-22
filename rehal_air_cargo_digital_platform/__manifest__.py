# -*- coding: utf-8 -*-
{
    'name': 'Rehal Air Cargo Digital Platform',
    'version': '18.0.1.0.0',
    'category': 'Logistics',
    'summary': 'Complete Freight Management System for Air Transport',
    'description': """
        Rehal Air Cargo Digital Platform
        =================================
        
        A complete solution for managing freight bookings across air transport.
        This module enables businesses to streamline logistics operations, from 
        calculating shipment costs to organizing and tracking shipments.
        
        Features:
        ---------
        * Flight Management: Create and manage flights with detailed information
        * Spot Management: Track available spots in each flight with color-coded status
        * Booking System: Book freight spots with automatic cost calculation
        * Public Web Portal: Allow customers to view flights and book spots online
        * Booking Validation: Prevent bookings less than 2 hours before takeoff
        * Status Tracking: Real-time status of spots (Full, Partial, Empty)
        * Cost Calculation: Automatic shipment cost calculation
    """,
    'author': 'LAFT',
    'website': 'https://www.laft.com',
    'depends': [
        'base',
        'sale',
        'account',
        'stock',
        'website',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/rehal_security.xml',
        'data/ir_sequence_data.xml',
        'views/rehal_shipment_views.xml',
        'views/rehal_spot_views.xml',
        'views/rehal_flight_views.xml',
        'views/rehal_menu_views.xml',
        'views/rehal_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'rehal_air_cargo_digital_platform/static/src/css/rehal_styles.css',
            'rehal_air_cargo_digital_platform/static/src/js/rehal_flight.js',
        ],
        'web.assets_frontend': [
            'rehal_air_cargo_digital_platform/static/src/css/rehal_public.css',
            'rehal_air_cargo_digital_platform/static/src/js/rehal_public.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
