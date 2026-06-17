# -*- coding: utf-8 -*-

from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class IrHttpOverride(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        """Override web_enterprise session_info to prevent expiration warnings"""
        try:
            # Get the original session info
            result = super().session_info()
            
            # Check if our database expiration remover is active
            remover = self.env['database.expiration.remover'].search([('is_active', '=', True)], limit=1)
            core = self.env['database.expiration.core'].search([('is_active', '=', True)], limit=1)
            
            if remover or core:
                # Override expiration-related fields to prevent warnings
                result['warning'] = False
                result['expiration_date'] = None
                result['expiration_reason'] = None
                
                # Set a far future expiration date to prevent any warnings
                future_date = '2099-12-31 23:59:59'
                result['expiration_date'] = future_date
                
                _logger.info("Database expiration warnings disabled by database_expiration_remover")
                
                # Add our custom support URL
                result['support_url'] = "https://www.yourcompany.com/support"
                
                # Add custom message indicating protection is active
                result['database_protection'] = {
                    'active': True,
                    'message': 'Database expiration protection is active',
                    'protected_by': 'database_expiration_remover'
                }
            
            return result
            
        except Exception as e:
            _logger.error(f"Error in session_info override: {e}")
            # Fallback to original behavior if there's an error
            return super().session_info()
    
    def webclient_rendering_context(self):
        """Override web_enterprise webclient_rendering_context to prevent expiration checks"""
        try:
            # Get the original context
            context = super().webclient_rendering_context()
            
            # Check if our protection is active
            remover = self.env['database.expiration.remover'].search([('is_active', '=', True)], limit=1)
            core = self.env['database.expiration.core'].search([('is_active', '=', True)], limit=1)
            
            if remover or core:
                # Override session info to remove expiration warnings
                if 'session_info' in context:
                    context['session_info']['warning'] = False
                    context['session_info']['expiration_date'] = None
                    context['session_info']['expiration_reason'] = None
                    
                    # Set far future date
                    context['session_info']['expiration_date'] = '2099-12-31 23:59:59'
                    
                    # Add protection info
                    context['session_info']['database_protection'] = {
                        'active': True,
                        'message': 'Database expiration protection is active',
                        'protected_by': 'database_expiration_remover'
                    }
                
                _logger.info("Webclient rendering context updated to prevent expiration warnings")
            
            return context
            
        except Exception as e:
            _logger.error(f"Error in webclient_rendering_context override: {e}")
            return super().webclient_rendering_context()
