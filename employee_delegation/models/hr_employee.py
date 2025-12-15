# -*- coding: utf-8 -*-

from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    
    delegation_ids = fields.One2many(
        'hr.employee.delegation',
        'employee_id',
        string='Delegations',
        help='List of delegations for this employee'
    )
    
    delegation_count = fields.Integer(
        string='Delegations',
        compute='_compute_delegation_count'
    )
    
    active_delegation_id = fields.Many2one(
        'hr.employee.delegation',
        string='Active Delegation',
        compute='_compute_active_delegation'
    )
    
    has_active_delegation = fields.Boolean(
        string='Has Active Delegation',
        compute='_compute_active_delegation'
    )
    
    # Work Statistics
    assigned_tasks_count = fields.Integer(
        string='Assigned Tasks',
        compute='_compute_work_statistics',
        help='Number of tasks assigned to this employee'
    )
    
    assigned_projects_count = fields.Integer(
        string='Assigned Projects',
        compute='_compute_work_statistics',
        help='Number of projects assigned to this employee'
    )
    
    assigned_opportunities_count = fields.Integer(
        string='Assigned Opportunities',
        compute='_compute_work_statistics',
        help='Number of opportunities assigned to this employee'
    )
    
    assigned_activities_count = fields.Integer(
        string='Assigned Activities',
        compute='_compute_work_statistics',
        help='Number of activities assigned to this employee'
    )
    
    @api.depends('delegation_ids')
    def _compute_delegation_count(self):
        for employee in self:
            employee.delegation_count = len(employee.delegation_ids)
    
    @api.depends('delegation_ids.is_current')
    def _compute_active_delegation(self):
        for employee in self:
            active = employee.delegation_ids.filtered('is_current')
            employee.active_delegation_id = active[:1] if active else False
            employee.has_active_delegation = bool(active)
    
    @api.depends('user_id')
    def _compute_work_statistics(self):
        for employee in self:
            if employee.user_id:
                # Count assigned tasks
                employee.assigned_tasks_count = self.env['project.task'].search_count([
                    ('user_ids', 'in', [employee.user_id.id])
                ])
                
                # Count assigned projects (projects where employee is assigned to tasks)
                project_ids = self.env['project.task'].search([
                    ('user_ids', 'in', [employee.user_id.id])
                ]).mapped('project_id.id')
                employee.assigned_projects_count = len(set(project_ids))
                
                # Count assigned opportunities
                employee.assigned_opportunities_count = self.env['crm.lead'].search_count([
                    ('user_id', '=', employee.user_id.id),
                    ('type', '=', 'opportunity')
                ])
                
                # Count assigned activities
                employee.assigned_activities_count = self.env['mail.activity'].search_count([
                    ('user_id', '=', employee.user_id.id)
                ])
            else:
                employee.assigned_tasks_count = 0
                employee.assigned_projects_count = 0
                employee.assigned_opportunities_count = 0
                employee.assigned_activities_count = 0
    
    def refresh_work_statistics(self):
        """Manually refresh work statistics for this employee"""
        self.ensure_one()
        self._compute_work_statistics()
        return True
    
    @api.model
    def update_work_statistics_for_user(self, user_id):
        """Update work statistics for all employees with this user_id"""
        employees = self.search([('user_id', '=', user_id)])
        for employee in employees:
            employee._compute_work_statistics()
        return True
    
    def action_view_delegations(self):
        """Open delegations for this employee"""
        self.ensure_one()
        return {
            'name': 'Delegations',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee.delegation',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id}
        }
    
    def action_view_assigned_tasks(self):
        """Open assigned tasks for this employee"""
        self.ensure_one()
        return {
            'name': 'Assigned Tasks',
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'view_mode': 'kanban,list,form',
            'domain': [('user_ids', 'in', [self.user_id.id])],
            'context': {'default_user_ids': [(6, 0, [self.user_id.id])]}
        }
    
    def action_view_assigned_projects(self):
        """Open assigned projects for this employee"""
        self.ensure_one()
        project_ids = self.env['project.task'].search([
            ('user_ids', 'in', [self.user_id.id])
        ]).mapped('project_id.id')
        return {
            'name': 'Assigned Projects',
            'type': 'ir.actions.act_window',
            'res_model': 'project.project',
            'view_mode': 'kanban,list,form',
            'domain': [('id', 'in', project_ids)],
        }
    
    def action_view_assigned_opportunities(self):
        """Open assigned opportunities for this employee"""
        self.ensure_one()
        return {
            'name': 'Assigned Opportunities',
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'view_mode': 'kanban,list,form',
            'domain': [('user_id', '=', self.user_id.id), ('type', '=', 'opportunity')],
            'context': {'default_user_id': self.user_id.id}
        }
    
    def action_view_assigned_activities(self):
        """Open assigned activities for this employee"""
        self.ensure_one()
        return {
            'name': 'Assigned Activities',
            'type': 'ir.actions.act_window',
            'res_model': 'mail.activity',
            'view_mode': 'list,form',
            'domain': [('user_id', '=', self.user_id.id)],
        }

