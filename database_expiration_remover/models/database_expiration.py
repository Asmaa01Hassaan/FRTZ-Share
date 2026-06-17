# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import datetime
from datetime import timedelta

_logger = logging.getLogger(__name__)


class DatabaseExpirationRemover(models.Model):
    _name = 'database.expiration.remover'
    _description = 'Database Expiration Remover'
    _rec_name = 'name'

    name = fields.Char(string='Name', required=True, default='Database Expiration Remover')
    is_active = fields.Boolean(string='Active', default=True, help='Enable/disable expiration removal')
    trial_extension_days = fields.Integer(string='Trial Extension Days', default=30, help='Number of days to extend trial period')
    last_extension_date = fields.Datetime(string='Last Extension Date', readonly=True)
    next_extension_date = fields.Datetime(string='Next Extension Date', compute='_compute_next_extension_date', store=True)
    extension_count = fields.Integer(string='Extension Count', default=0, readonly=True)
    database_expiration_date = fields.Datetime(string='Database Expiration Date', readonly=True)
    is_expired = fields.Boolean(string='Is Expired', compute='_compute_is_expired', store=True)
    
    @api.depends('last_extension_date', 'trial_extension_days')
    def _compute_next_extension_date(self):
        for record in self:
            if record.last_extension_date:
                record.next_extension_date = record.last_extension_date + timedelta(days=record.trial_extension_days)
            else:
                record.next_extension_date = fields.Datetime.now() + timedelta(days=record.trial_extension_days)
    
    @api.depends('database_expiration_date')
    def _compute_is_expired(self):
        for record in self:
            if record.database_expiration_date:
                record.is_expired = fields.Datetime.now() > record.database_expiration_date
            else:
                record.is_expired = False
    
    def action_extend_trial(self):
        """Extend the trial period"""
        self.ensure_one()
        try:
            # Get the current database expiration date
            current_expiration = self._get_database_expiration_date()
            
            if current_expiration:
                # Extend the trial period
                new_expiration = current_expiration + timedelta(days=self.trial_extension_days)
                self._set_database_expiration_date(new_expiration)
                
                # Update record
                self.write({
                    'last_extension_date': fields.Datetime.now(),
                    'extension_count': self.extension_count + 1,
                    'database_expiration_date': new_expiration,
                })
                
                _logger.info(f"Trial extended by {self.trial_extension_days} days. New expiration: {new_expiration}")
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Trial period extended by %s days') % self.trial_extension_days,
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                # Set initial expiration date
                new_expiration = fields.Datetime.now() + timedelta(days=self.trial_extension_days)
                self._set_database_expiration_date(new_expiration)
                
                self.write({
                    'last_extension_date': fields.Datetime.now(),
                    'extension_count': 1,
                    'database_expiration_date': new_expiration,
                })
                
                _logger.info(f"Initial trial period set for {self.trial_extension_days} days. Expiration: {new_expiration}")
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Initial trial period set for %s days') % self.trial_extension_days,
                        'type': 'success',
                        'sticky': False,
                    }
                }
                
        except Exception as e:
            _logger.error(f"Error extending trial: {e}")
            raise UserError(_('Error extending trial period: %s') % str(e))
    
    def action_reset_expiration(self):
        """Reset the expiration date to a new trial period"""
        self.ensure_one()
        try:
            # Set new expiration date
            new_expiration = fields.Datetime.now() + timedelta(days=self.trial_extension_days)
            self._set_database_expiration_date(new_expiration)
            
            # Update record
            self.write({
                'last_extension_date': fields.Datetime.now(),
                'extension_count': self.extension_count + 1,
                'database_expiration_date': new_expiration,
            })
            
            _logger.info(f"Expiration date reset. New expiration: {new_expiration}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Expiration date reset successfully'),
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.error(f"Error resetting expiration: {e}")
            raise UserError(_('Error resetting expiration date: %s') % str(e))
    
    def _get_database_expiration_date(self):
        """Get the current database expiration date"""
        try:
            # Try to get expiration date from system parameters
            expiration_param = self.env['ir.config_parameter'].sudo().get_param('database.expiration_date')
            if expiration_param:
                return fields.Datetime.from_string(expiration_param)
            return None
        except Exception as e:
            _logger.error(f"Error getting database expiration date: {e}")
            return None
    
    def _set_database_expiration_date(self, expiration_date):
        """Set the database expiration date"""
        try:
            # Set expiration date in system parameters
            self.env['ir.config_parameter'].sudo().set_param('database.expiration_date', expiration_date.strftime('%Y-%m-%d %H:%M:%S'))
            
            # Also try to set it in the database directly
            self.env.cr.execute("""
                UPDATE ir_config_parameter 
                SET value = %s 
                WHERE key = 'database.expiration_date'
            """, (expiration_date.strftime('%Y-%m-%d %H:%M:%S'),))
            
            self.env.cr.commit()
            
        except Exception as e:
            _logger.error(f"Error setting database expiration date: {e}")
            raise
    
    def action_auto_extend_trial(self):
        """Automatically extend trial if needed"""
        self.ensure_one()
        if not self.is_active:
            return
        
        current_expiration = self._get_database_expiration_date()
        if current_expiration and fields.Datetime.now() > current_expiration:
            # Trial has expired, extend it
            self.action_extend_trial()
        elif current_expiration and (current_expiration - fields.Datetime.now()).days <= 7:
            # Trial expires in 7 days or less, extend it
            self.action_extend_trial()
    
    @api.model
    def _cron_auto_extend_trial(self):
        """Cron job to automatically extend trial"""
        try:
            records = self.search([('is_active', '=', True)])
            for record in records:
                record.action_auto_extend_trial()
        except Exception as e:
            _logger.error(f"Error in auto extend trial cron: {e}")
    
    @api.model
    def create(self, vals):
        """Override create to set initial values"""
        if not vals.get('name'):
            vals['name'] = 'Database Expiration Remover'
        record = super().create(vals)
        
        # Create cron jobs if this is the first record
        if len(self.search([])) == 1:
            record._create_cron_jobs()
        
        return record
    
    def _create_cron_jobs(self):
        """Create cron jobs programmatically"""
        try:
            # Create auto extend trial cron job
            self.env['ir.cron'].create({
                'name': 'Auto Extend Database Trial',
                'model_id': self.env['ir.model'].search([('model', '=', 'database.expiration.remover')]).id,
                'state': 'code',
                'code': 'model._cron_auto_extend_trial()',
                'interval_number': 1,
                'interval_type': 'days',
                'number_call': -1,
                'active': True,
                'doall': False,
            })
            
            _logger.info("Created auto extend trial cron job")
            
        except Exception as e:
            _logger.error(f"Error creating cron jobs: {e}")
    
    @api.model
    def _auto_create_cron_jobs(self):
        """Auto create cron jobs when module is installed"""
        try:
            # Check if cron jobs already exist
            existing_cron = self.env['ir.cron'].search([('name', '=', 'Auto Extend Database Trial')])
            if not existing_cron:
                # Create a default record to trigger cron job creation
                if not self.search([]):
                    self.create({
                        'name': 'Database Expiration Remover',
                        'is_active': True,
                        'trial_extension_days': 30,
                    })
        except Exception as e:
            _logger.error(f"Error auto creating cron jobs: {e}")
    
    def write(self, vals):
        """Override write to handle expiration updates"""
        result = super().write(vals)
        
        # If trial extension days changed, update next extension date
        if 'trial_extension_days' in vals:
            self._compute_next_extension_date()
        
        return result


class IrConfigParameter(models.Model):
    _inherit = 'ir.config_parameter'
    
    def _check_database_expiration(self):
        """Override to prevent database expiration checks"""
        try:
            # Get the expiration remover record
            remover = self.env['database.expiration.remover'].search([('is_active', '=', True)], limit=1)
            if remover:
                # Check if we need to extend the trial
                remover.action_auto_extend_trial()
                return True
        except Exception as e:
            _logger.error(f"Error in database expiration check: {e}")
        
        return True
