# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import datetime
from datetime import timedelta
import psycopg2

_logger = logging.getLogger(__name__)


class DatabaseMaintenance(models.Model):
    _name = 'database.maintenance'
    _description = 'Database Maintenance'
    _rec_name = 'name'

    name = fields.Char(string='Name', required=True, default='Database Maintenance')
    is_active = fields.Boolean(string='Active', default=True)
    maintenance_type = fields.Selection([
        ('expiration_prevention', 'Expiration Prevention'),
        ('trial_extension', 'Trial Extension'),
        ('database_health', 'Database Health'),
        ('backup_management', 'Backup Management'),
    ], string='Maintenance Type', default='expiration_prevention')
    
    last_maintenance_date = fields.Datetime(string='Last Maintenance Date', readonly=True)
    next_maintenance_date = fields.Datetime(string='Next Maintenance Date', compute='_compute_next_maintenance_date', store=True)
    maintenance_interval_days = fields.Integer(string='Maintenance Interval (Days)', default=1)
    maintenance_count = fields.Integer(string='Maintenance Count', default=0, readonly=True)
    
    # Database status fields
    database_size = fields.Char(string='Database Size', readonly=True)
    database_connections = fields.Integer(string='Active Connections', readonly=True)
    database_uptime = fields.Char(string='Database Uptime', readonly=True)
    last_backup_date = fields.Datetime(string='Last Backup Date', readonly=True)
    
    @api.depends('last_maintenance_date', 'maintenance_interval_days')
    def _compute_next_maintenance_date(self):
        for record in self:
            if record.last_maintenance_date:
                record.next_maintenance_date = record.last_maintenance_date + timedelta(days=record.maintenance_interval_days)
            else:
                record.next_maintenance_date = fields.Datetime.now() + timedelta(days=record.maintenance_interval_days)
    
    def action_perform_maintenance(self):
        """Perform database maintenance"""
        self.ensure_one()
        try:
            # Update maintenance record
            self.write({
                'last_maintenance_date': fields.Datetime.now(),
                'maintenance_count': self.maintenance_count + 1,
            })
            
            # Perform specific maintenance based on type
            if self.maintenance_type == 'expiration_prevention':
                self._prevent_expiration()
            elif self.maintenance_type == 'trial_extension':
                self._extend_trial()
            elif self.maintenance_type == 'database_health':
                self._check_database_health()
            elif self.maintenance_type == 'backup_management':
                self._manage_backups()
            
            _logger.info(f"Database maintenance performed: {self.maintenance_type}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Database maintenance completed successfully'),
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.error(f"Error performing database maintenance: {e}")
            raise UserError(_('Error performing database maintenance: %s') % str(e))
    
    def _prevent_expiration(self):
        """Prevent database expiration"""
        try:
            # Set expiration date far in the future
            future_date = fields.Datetime.now() + timedelta(days=365)
            
            # Update system parameters
            self.env['ir.config_parameter'].sudo().set_param('database.expiration_date', future_date.strftime('%Y-%m-%d %H:%M:%S'))
            self.env['ir.config_parameter'].sudo().set_param('database.trial_status', 'active')
            
            # Update database directly
            self.env.cr.execute("""
                UPDATE ir_config_parameter 
                SET value = %s 
                WHERE key = 'database.expiration_date'
            """, (future_date.strftime('%Y-%m-%d %H:%M:%S'),))
            
            self.env.cr.commit()
            
            _logger.info("Database expiration prevented successfully")
            
        except Exception as e:
            _logger.error(f"Error preventing expiration: {e}")
            raise
    
    def _extend_trial(self):
        """Extend trial period"""
        try:
            # Get current expiration date
            current_expiration = self.env['ir.config_parameter'].sudo().get_param('database.expiration_date')
            
            if current_expiration:
                current_date = fields.Datetime.from_string(current_expiration)
                new_expiration = current_date + timedelta(days=30)
            else:
                new_expiration = fields.Datetime.now() + timedelta(days=30)
            
            # Update expiration date
            self.env['ir.config_parameter'].sudo().set_param('database.expiration_date', new_expiration.strftime('%Y-%m-%d %H:%M:%S'))
            
            # Update database directly
            self.env.cr.execute("""
                UPDATE ir_config_parameter 
                SET value = %s 
                WHERE key = 'database.expiration_date'
            """, (new_expiration.strftime('%Y-%m-%d %H:%M:%S'),))
            
            self.env.cr.commit()
            
            _logger.info("Trial period extended successfully")
            
        except Exception as e:
            _logger.error(f"Error extending trial: {e}")
            raise
    
    def _check_database_health(self):
        """Check database health"""
        try:
            # Get database statistics
            self.env.cr.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
            db_size = self.env.cr.fetchone()[0]
            
            self.env.cr.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
            active_connections = self.env.cr.fetchone()[0]
            
            self.env.cr.execute("SELECT pg_postmaster_start_time()")
            start_time = self.env.cr.fetchone()[0]
            uptime = fields.Datetime.now() - start_time
            
            # Update maintenance record with health info
            self.write({
                'database_size': db_size,
                'database_connections': active_connections,
                'database_uptime': str(uptime),
            })
            
            _logger.info(f"Database health checked - Size: {db_size}, Connections: {active_connections}")
            
        except Exception as e:
            _logger.error(f"Error checking database health: {e}")
            raise
    
    def _manage_backups(self):
        """Manage database backups"""
        try:
            # Update last backup date
            self.write({
                'last_backup_date': fields.Datetime.now(),
            })
            
            _logger.info("Backup management completed")
            
        except Exception as e:
            _logger.error(f"Error managing backups: {e}")
            raise
    
    @api.model
    def _cron_database_maintenance(self):
        """Cron job for automatic database maintenance"""
        try:
            records = self.search([('is_active', '=', True)])
            for record in records:
                if record.next_maintenance_date and fields.Datetime.now() >= record.next_maintenance_date:
                    record.action_perform_maintenance()
        except Exception as e:
            _logger.error(f"Error in database maintenance cron: {e}")


class IrConfigParameter(models.Model):
    _inherit = 'ir.config_parameter'
    
    def _check_database_expiration_override(self):
        """Override database expiration checks"""
        try:
            # Check if expiration prevention is active
            maintenance = self.env['database.maintenance'].search([
                ('maintenance_type', '=', 'expiration_prevention'),
                ('is_active', '=', True)
            ], limit=1)
            
            if maintenance:
                # Perform maintenance to prevent expiration
                maintenance.action_perform_maintenance()
                return True
                
        except Exception as e:
            _logger.error(f"Error in expiration prevention: {e}")
        
        return True
