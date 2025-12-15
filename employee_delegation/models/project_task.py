# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProjectTask(models.Model):
    _inherit = 'project.task'
    
    delegated_user_id = fields.Many2one(
        'res.users',
        string='Delegated To',
        tracking=True,
        help='User to whom this task is temporarily delegated'
    )
    
    is_delegated = fields.Boolean(
        string='Is Delegated',
        compute='_compute_is_delegated',
        search='_search_is_delegated',
        help='Whether this task is currently delegated'
    )
    
    delegation_info = fields.Char(
        string='Delegation Info',
        compute='_compute_delegation_info',
        help='Information about the delegation'
    )
    
    @api.depends('delegated_user_id')
    def _compute_is_delegated(self):
        for task in self:
            task.is_delegated = bool(task.delegated_user_id)
    
    def _search_is_delegated(self, operator, value):
        if operator == '=' and value:
            return [('delegated_user_id', '!=', False)]
        elif operator == '=' and not value:
            return [('delegated_user_id', '=', False)]
        return []
    
    @api.depends('user_ids', 'delegated_user_id')
    def _compute_delegation_info(self):
        for task in self:
            if task.delegated_user_id and task.user_ids:
                original_user = task.user_ids[0] if task.user_ids else False
                if original_user:
                    task.delegation_info = 'مفوّضة من: %s' % original_user.name
                else:
                    task.delegation_info = False
            else:
                task.delegation_info = False
    
    @api.model
    def create(self, vals):
        """Override create to update work statistics"""
        task = super().create(vals)
        if 'user_ids' in vals and vals['user_ids']:
            # Update work statistics for assigned users
            for user_id in task.user_ids.ids:
                self.env['hr.employee'].update_work_statistics_for_user(user_id)
        return task
    
    def write(self, vals):
        """Override write to update work statistics when user_ids change"""
        old_user_ids = set()
        if 'user_ids' in vals:
            # Get old user_ids before update
            for task in self:
                old_user_ids.update(task.user_ids.ids)
        
        result = super().write(vals)
        
        if 'user_ids' in vals:
            # Get new user_ids after update
            new_user_ids = set()
            for task in self:
                new_user_ids.update(task.user_ids.ids)
            
            # Update statistics for all affected users
            all_affected_users = old_user_ids.union(new_user_ids)
            for user_id in all_affected_users:
                self.env['hr.employee'].update_work_statistics_for_user(user_id)
        
        return result

