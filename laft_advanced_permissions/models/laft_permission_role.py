# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class LaftPermissionRole(models.Model):
    _name = 'laft.permission.role'
    _description = 'Permission Role Template'
    _order = 'sequence, name'
    
    name = fields.Char('Role Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=10)
    description = fields.Text('Description', translate=True)
    active = fields.Boolean('Active', default=True)
    
    # Icon for UI
    icon = fields.Char('Icon', default='fa-user')
    color = fields.Integer('Color Index', default=0)
    
    # Project Settings
    project_access = fields.Selection([
        ('none', 'No Access'),
        ('user', 'User - Own Projects'),
        ('manager', 'Manager - Own Projects'),
        ('finance', 'Manager + Finance'),
        ('general', 'General Manager - All')
    ], string='Project Access', default='none')
    
    project_see_all = fields.Boolean('See All Projects')
    can_create_projects = fields.Boolean('Create Projects')
    can_manage_tasks = fields.Boolean('Manage Tasks', default=True)
    can_view_bills = fields.Boolean('View Bills')
    can_create_bills = fields.Boolean('Create Bills')
    can_approve_bills = fields.Boolean('Approve Bills')
    
    # BD Settings
    bd_access = fields.Selection([
        ('none', 'No Access'),
        ('user', 'User - Own'),
        ('manager', 'Manager - Team'),
        ('executive', 'Executive - All')
    ], string='BD Access', default='none')
    
    # Finance Settings
    finance_access = fields.Selection([
        ('none', 'No Access'),
        ('project_only', 'Project-Related'),
        ('invoicing', 'Invoicing'),
        ('accounting', 'Accounting')
    ], string='Finance Access', default='none')
    
    # Admin Settings
    is_admin = fields.Boolean('System Administrator')
    can_manage_permissions = fields.Boolean('Manage Permissions')
    
    # Dashboard Access
    dashboard_my = fields.Boolean('My Dashboard', default=True)
    dashboard_projects = fields.Boolean('Projects Dashboard')
    dashboard_bd = fields.Boolean('BD Dashboard')
    dashboard_executive = fields.Boolean('Executive Dashboard')
    
    # Groups (technical)
    group_ids = fields.Many2many(
        'res.groups',
        string='Technical Groups',
        help="Groups that will be applied when this role is assigned"
    )
    
    # Usage tracking
    user_count = fields.Integer(
        'Users with this Role',
        compute='_compute_user_count'
    )
    
    @api.depends('name')
    def _compute_user_count(self):
        """Count how many users have settings matching this role"""
        for role in self:
            # This is a simplified count - in reality we'd check all fields
            role.user_count = 0
    
    def action_apply_to_user(self):
        """Open wizard to apply this role to selected users"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Apply Role to Users'),
            'res_model': 'laft.permission.role.apply.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_role_id': self.id,
            }
        }

