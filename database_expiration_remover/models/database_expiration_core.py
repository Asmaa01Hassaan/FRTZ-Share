# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import datetime
from datetime import timedelta
import psycopg2

_logger = logging.getLogger(__name__)


class DatabaseExpirationCore(models.Model):
    _name = 'database.expiration.core'
    _description = 'Database Expiration Core'
    _rec_name = 'name'

    name = fields.Char(string='Name', required=True, default='Database Expiration Core')
    is_active = fields.Boolean(string='Active', default=True)
    prevention_method = fields.Selection([
        ('parameter_override', 'Parameter Override'),
        ('database_direct', 'Database Direct'),
        ('system_hook', 'System Hook'),
        ('cron_override', 'Cron Override'),
    ], string='Prevention Method', default='parameter_override')
    
    last_prevention_date = fields.Datetime(string='Last Prevention Date', readonly=True)
    prevention_count = fields.Integer(string='Prevention Count', default=0, readonly=True)
    prevention_interval_hours = fields.Integer(string='Prevention Interval (Hours)', default=1)
    
    # System parameters
    expiration_date_override = fields.Datetime(string='Expiration Date Override', default=lambda self: fields.Datetime.now() + timedelta(days=365))
    trial_status_override = fields.Selection([
        ('active', 'Active'),
        ('extended', 'Extended'),
        ('permanent', 'Permanent'),
    ], string='Trial Status Override', default='permanent')
    
    @api.model
    def _prevent_database_expiration(self):
        """Core method to prevent database expiration"""
        try:
            # Method 1: Parameter Override
            if self.prevention_method == 'parameter_override':
                self._override_system_parameters()
            
            # Method 2: Database Direct
            elif self.prevention_method == 'database_direct':
                self._direct_database_override()
            
            # Method 3: System Hook
            elif self.prevention_method == 'system_hook':
                self._system_hook_override()
            
            # Method 4: Cron Override
            elif self.prevention_method == 'cron_override':
                self._cron_override()
            
            # Update prevention record
            self.write({
                'last_prevention_date': fields.Datetime.now(),
                'prevention_count': self.prevention_count + 1,
            })
            
            _logger.info("Database expiration prevented successfully")
            return True
            
        except Exception as e:
            _logger.error(f"Error preventing database expiration: {e}")
            return False
    
    def _override_system_parameters(self):
        """Override system parameters to prevent expiration"""
        try:
            # Set expiration date far in the future
            future_date = self.expiration_date_override or (fields.Datetime.now() + timedelta(days=365))
            
            # Update system parameters
            self.env['ir.config_parameter'].sudo().set_param('database.expiration_date', future_date.strftime('%Y-%m-%d %H:%M:%S'))
            self.env['ir.config_parameter'].sudo().set_param('database.trial_status', self.trial_status_override)
            self.env['ir.config_parameter'].sudo().set_param('database.trial_start_date', fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            # Set additional parameters
            self.env['ir.config_parameter'].sudo().set_param('database.expiration_prevented', 'true')
            self.env['ir.config_parameter'].sudo().set_param('database.last_prevention', fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            _logger.info("System parameters overridden successfully")
            
        except Exception as e:
            _logger.error(f"Error overriding system parameters: {e}")
            raise
    
    def _direct_database_override(self):
        """Direct database override to prevent expiration"""
        try:
            # Set expiration date far in the future
            future_date = self.expiration_date_override or (fields.Datetime.now() + timedelta(days=365))
            
            # Direct database update
            self.env.cr.execute("""
                INSERT INTO ir_config_parameter (key, value, create_uid, create_date, write_uid, write_date)
                VALUES ('database.expiration_date', %s, 1, NOW(), 1, NOW())
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, write_date = NOW()
            """, (future_date.strftime('%Y-%m-%d %H:%M:%S'),))
            
            self.env.cr.execute("""
                INSERT INTO ir_config_parameter (key, value, create_uid, create_date, write_uid, write_date)
                VALUES ('database.trial_status', %s, 1, NOW(), 1, NOW())
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, write_date = NOW()
            """, (self.trial_status_override,))
            
            self.env.cr.execute("""
                INSERT INTO ir_config_parameter (key, value, create_uid, create_date, write_uid, write_date)
                VALUES ('database.expiration_prevented', 'true', 1, NOW(), 1, NOW())
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, write_date = NOW()
            """)
            
            self.env.cr.commit()
            
            _logger.info("Database directly overridden successfully")
            
        except Exception as e:
            _logger.error(f"Error in direct database override: {e}")
            raise
    
    def _system_hook_override(self):
        """System hook override to prevent expiration"""
        try:
            # Override system methods
            self._override_expiration_checks()
            
            _logger.info("System hooks overridden successfully")
            
        except Exception as e:
            _logger.error(f"Error in system hook override: {e}")
            raise
    
    def _cron_override(self):
        """Cron override to prevent expiration"""
        try:
            # Set up continuous prevention
            self._setup_continuous_prevention()
            
            _logger.info("Cron override set up successfully")
            
        except Exception as e:
            _logger.error(f"Error in cron override: {e}")
            raise
    
    def _override_expiration_checks(self):
        """Override expiration check methods"""
        try:
            # Override core expiration checks
            self.env.cr.execute("""
                CREATE OR REPLACE FUNCTION check_database_expiration()
                RETURNS boolean AS $$
                BEGIN
                    RETURN false; -- Always return false to prevent expiration
                END;
                $$ LANGUAGE plpgsql;
            """)
            
            _logger.info("Expiration checks overridden successfully")
            
        except Exception as e:
            _logger.error(f"Error overriding expiration checks: {e}")
            raise
    
    def _setup_continuous_prevention(self):
        """Set up continuous prevention"""
        try:
            # Create a cron job that runs every hour
            model_id = self.env['ir.model'].search([('model', '=', 'database.expiration.core')])
            if model_id:
                cron_job = self.env['ir.cron'].create({
                    'name': 'Continuous Database Expiration Prevention',
                    'model_id': model_id.id,
                    'state': 'code',
                    'code': 'model._prevent_database_expiration()',
                    'interval_number': 1,
                    'interval_type': 'hours',
                    'number_call': -1,
                    'active': True,
                    'doall': False,
                })
            
            _logger.info("Continuous prevention set up successfully")
            
        except Exception as e:
            _logger.error(f"Error setting up continuous prevention: {e}")
            raise
    
    @api.model
    def _cron_prevent_expiration(self):
        """Cron job to prevent expiration"""
        try:
            records = self.search([('is_active', '=', True)])
            for record in records:
                if record.last_prevention_date:
                    hours_since_last = (fields.Datetime.now() - record.last_prevention_date).total_seconds() / 3600
                    if hours_since_last >= record.prevention_interval_hours:
                        record._prevent_database_expiration()
                else:
                    record._prevent_database_expiration()
        except Exception as e:
            _logger.error(f"Error in expiration prevention cron: {e}")
    
    def action_prevent_expiration_now(self):
        """Manually prevent expiration"""
        self.ensure_one()
        try:
            result = self._prevent_database_expiration()
            if result:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Database expiration prevented successfully'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                raise UserError(_('Failed to prevent database expiration'))
        except Exception as e:
            _logger.error(f"Error preventing expiration: {e}")
            raise UserError(_('Error preventing database expiration: %s') % str(e))


class IrConfigParameter(models.Model):
    _inherit = 'ir.config_parameter'
    
    def _check_database_expiration_core(self):
        """Core method to check and prevent database expiration"""
        try:
            # Check if prevention is active
            core = self.env['database.expiration.core'].search([('is_active', '=', True)], limit=1)
            if core:
                # Prevent expiration
                core._prevent_database_expiration()
                return True
        except Exception as e:
            _logger.error(f"Error in core expiration prevention: {e}")
        
        return True
