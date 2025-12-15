# -*- coding: utf-8 -*-

from odoo import models, fields, api


class MailActivity(models.Model):
    _inherit = 'mail.activity'
    
    delegated_user_id = fields.Many2one(
        'res.users',
        string='Delegated To',
        help='User to whom this activity is temporarily delegated'
    )
    
    is_delegated = fields.Boolean(
        string='Is Delegated',
        compute='_compute_is_delegated',
        search='_search_is_delegated',
        help='Whether this activity is currently delegated'
    )
    
    delegation_info = fields.Char(
        string='Delegation Info',
        compute='_compute_delegation_info',
        help='Information about the delegation'
    )
    
    @api.depends('delegated_user_id')
    def _compute_is_delegated(self):
        for activity in self:
            activity.is_delegated = bool(activity.delegated_user_id)
    
    def _search_is_delegated(self, operator, value):
        if operator == '=' and value:
            return [('delegated_user_id', '!=', False)]
        elif operator == '=' and not value:
            return [('delegated_user_id', '=', False)]
        return []
    
    @api.depends('user_id', 'delegated_user_id')
    def _compute_delegation_info(self):
        for activity in self:
            if activity.delegated_user_id and activity.user_id:
                activity.delegation_info = 'مفوّضة من: %s' % activity.user_id.name
            else:
                activity.delegation_info = False
    
    @api.model
    def create(self, vals):
        """Override create to update work statistics"""
        activity = super().create(vals)
        if 'user_id' in vals and vals['user_id']:
            # Update work statistics for assigned user
            self.env['hr.employee'].update_work_statistics_for_user(vals['user_id'])
        return activity
    
    def write(self, vals):
        """Override write to update work statistics when user_id changes"""
        old_user_ids = set()
        if 'user_id' in vals:
            # Get old user_ids before update
            for activity in self:
                if activity.user_id:
                    old_user_ids.add(activity.user_id.id)
        
        result = super().write(vals)
        
        if 'user_id' in vals:
            # Get new user_ids after update
            new_user_ids = set()
            for activity in self:
                if activity.user_id:
                    new_user_ids.add(activity.user_id.id)
            
            # Update statistics for all affected users
            all_affected_users = old_user_ids.union(new_user_ids)
            for user_id in all_affected_users:
                self.env['hr.employee'].update_work_statistics_for_user(user_id)
        
        return result

