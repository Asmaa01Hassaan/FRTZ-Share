# -*- coding: utf-8 -*-
#############################################################################
#
#    WhatsApp Wedding Invitations Module
#
#    Copyright (C) 2024-TODAY
#    Author: Custom Development
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
#############################################################################
{
    'name': 'WhatsApp Wedding Invitations',
    'version': '18.0.1.0.0',
    'category': 'Marketing/Events',
    'summary': 'Send wedding invitations via WhatsApp without Meta API',
    'description': """
        WhatsApp Wedding Invitations Module
        ===================================
        
        This module allows you to:
        * Send wedding invitations via WhatsApp
        * Manage event guests
        * Send personalized invitations to multiple guests
        * Configure WhatsApp server settings
        * Track invitation sending status
        
        Features:
        * Integration with WhatsApp Web (no Meta API required)
        * Bulk invitation sending
        * Personalized messages with guest names
        * Guest management for events
        * Invitation status tracking
    """,
    'author': 'Custom Development',
    'depends': ['base', 'calendar', 'event', 'website'],
    'data': [
        'security/ir.model.access.csv',
        'views/calendar_event_views.xml',
        'views/event_event_views.xml',
        'views/event_registration_views.xml',
        'views/event_guest_views.xml',
        'views/res_config_settings_views.xml',
        'views/whatsapp_qr_session_views.xml',
        'views/templates/confirmation_templates.xml',
        'wizard/whatsapp_invitation_wizard_views.xml',
        'wizard/whatsapp_attachment_wizard_views.xml',
        'wizard/whatsapp_confirmation_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}



