# -*- coding: utf-8 -*-

from . import models


def post_init_hook(env):
    """Post-installation hook to create cron jobs and set dynamic dates"""
    import datetime
    
    # Set dynamic dates and config parameters
    try:
        # Set current date as trial start date
        current_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        env['ir.config_parameter'].sudo().set_param('database.trial_start_date', current_date)
        
        # Set expiration date to 30 days from now
        expiration_date = (datetime.datetime.now() + datetime.timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
        env['ir.config_parameter'].sudo().set_param('database.expiration_date', expiration_date)
        
        # Set database trial status
        env['ir.config_parameter'].sudo().set_param('database.trial_status', 'active')
        
        print("✅ Dynamic dates and config parameters set successfully")
        
    except Exception as e:
        print(f"❌ Error setting dynamic dates and config parameters: {e}")
    
    # Create cron jobs programmatically
    try:
        # Check if cron jobs already exist
        existing_cron = env['ir.cron'].search([('name', '=', 'Auto Extend Database Trial')])
        if not existing_cron:
            # Get the model ID
            model_id = env['ir.model'].search([('model', '=', 'database.expiration.remover')])
            if model_id:
                # Create auto extend trial cron job
                env['ir.cron'].create({
                    'name': 'Auto Extend Database Trial',
                    'model_id': model_id.id,
                    'state': 'code',
                    'code': 'model._cron_auto_extend_trial()',
                    'interval_number': 1,
                    'interval_type': 'days',
                    'number_call': -1,
                    'active': True,
                    'doall': False,
                })
                
                # Create database maintenance cron job
                maintenance_model_id = env['ir.model'].search([('model', '=', 'database.maintenance')])
                if maintenance_model_id:
                    env['ir.cron'].create({
                        'name': 'Database Maintenance',
                        'model_id': maintenance_model_id.id,
                        'state': 'code',
                        'code': 'model._cron_database_maintenance()',
                        'interval_number': 1,
                        'interval_type': 'hours',
                        'number_call': -1,
                        'active': True,
                        'doall': False,
                    })
                
                # Create core expiration prevention cron job
                core_model_id = env['ir.model'].search([('model', '=', 'database.expiration.core')])
                if core_model_id:
                    env['ir.cron'].create({
                        'name': 'Core Expiration Prevention',
                        'model_id': core_model_id.id,
                        'state': 'code',
                        'code': 'model._cron_prevent_expiration()',
                        'interval_number': 1,
                        'interval_type': 'hours',
                        'number_call': -1,
                        'active': True,
                        'doall': False,
                    })
                
                print("✅ Database expiration remover cron jobs created successfully")
            else:
                print("⚠️ Model 'database.expiration.remover' not found, skipping cron job creation")
        else:
            print("ℹ️ Cron jobs already exist, skipping creation")
            
    except Exception as e:
        print(f"❌ Error creating cron jobs: {e}")
