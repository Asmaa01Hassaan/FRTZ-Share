# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date
import logging

_logger = logging.getLogger(__name__)


class HrEmployeeDelegation(models.Model):
    _name = 'hr.employee.delegation'
    _description = 'Employee Delegation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc, id desc'
    _rec_name = 'display_name'
    
    # Basic Information
    employee_id = fields.Many2one(
        'hr.employee',
        string='Original Employee',
        required=True,
        ondelete='cascade',
        help='Employee who is delegating their work'
    )
    
    delegate_to_employee_id = fields.Many2one(
        'hr.employee',
        string='Delegate To',
        required=True,
        ondelete='cascade',
        help='Employee who will handle the delegated work'
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='Original User',
        related='employee_id.user_id',
        store=True,
        readonly=True
    )
    
    delegate_to_user_id = fields.Many2one(
        'res.users',
        string='Delegate To User',
        related='delegate_to_employee_id.user_id',
        store=True,
        readonly=True
    )
    
    # Date Range
    date_from = fields.Date(
        string='Start Date',
        required=True,
        default=fields.Date.context_today,
        help='Delegation start date'
    )
    
    date_to = fields.Date(
        string='End Date',
        required=True,
        help='Delegation end date'
    )
    
    # State Management
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Uncheck to archive this delegation'
    )
    
    # Reason
    reason = fields.Selection([
        ('vacation', 'Vacation'),
        ('sick_leave', 'Sick Leave'),
        ('resignation', 'Resignation'),
        ('training', 'Training'),
        ('other', 'Other'),
    ], string='Reason', required=True, default='vacation')
    
    notes = fields.Text(
        string='Notes',
        help='Additional information about this delegation'
    )
    
    # Computed Fields
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    is_current = fields.Boolean(
        string='Is Current',
        compute='_compute_is_current',
        search='_search_is_current',
        help='Whether this delegation is currently active'
    )
    
    # Statistics
    delegated_opportunities_count = fields.Integer(
        string='Opportunities',
        compute='_compute_delegated_counts'
    )
    
    delegated_tasks_count = fields.Integer(
        string='Tasks',
        compute='_compute_delegated_counts'
    )
    
    delegated_activities_count = fields.Integer(
        string='Activities',
        compute='_compute_delegated_counts'
    )
    
    @api.depends('employee_id', 'delegate_to_employee_id', 'date_from', 'date_to')
    def _compute_display_name(self):
        for record in self:
            if record.employee_id and record.delegate_to_employee_id:
                record.display_name = _('%s → %s (%s to %s)') % (
                    record.employee_id.name,
                    record.delegate_to_employee_id.name,
                    record.date_from or '',
                    record.date_to or ''
                )
            else:
                record.display_name = _('New Delegation')
    
    @api.depends('date_from', 'date_to', 'state')
    def _compute_is_current(self):
        today = date.today()
        for record in self:
            record.is_current = (
                record.state == 'active' and
                record.date_from <= today <= record.date_to
            )
    
    @api.model
    def write(self, vals):
        """Override write to handle state changes"""
        result = super().write(vals)
        
        # Handle state changes
        if 'state' in vals:
            for record in self:
                if vals['state'] == 'active':
                    record._apply_delegation()
                elif vals['state'] in ['expired', 'cancelled']:
                    record._remove_delegation()
        
        return result
    
    def _search_is_current(self, operator, value):
        today = date.today()
        if operator == '=' and value:
            return [
                ('state', '=', 'active'),
                ('date_from', '<=', today),
                ('date_to', '>=', today)
            ]
        return []
    
    def _compute_delegated_counts(self):
        for record in self:
            if record.delegate_to_user_id:
                record.delegated_opportunities_count = self.env['crm.lead'].search_count([
                    ('delegated_user_id', '=', record.delegate_to_user_id.id)
                ])
                record.delegated_tasks_count = self.env['project.task'].search_count([
                    ('delegated_user_id', '=', record.delegate_to_user_id.id)
                ])
                record.delegated_activities_count = self.env['mail.activity'].search_count([
                    ('delegated_user_id', '=', record.delegate_to_user_id.id)
                ])
            else:
                record.delegated_opportunities_count = 0
                record.delegated_tasks_count = 0
                record.delegated_activities_count = 0
    
    @api.constrains('employee_id', 'delegate_to_employee_id')
    def _check_employees(self):
        for record in self:
            if record.employee_id == record.delegate_to_employee_id:
                raise ValidationError(_('Employee cannot delegate to themselves.'))
    
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from and record.date_to and record.date_from > record.date_to:
                raise ValidationError(_('End date must be after start date.'))
    
    @api.constrains('employee_id', 'date_from', 'date_to', 'state')
    def _check_overlapping_delegations(self):
        for record in self:
            if record.state in ['draft', 'active']:
                overlapping = self.search([
                    ('id', '!=', record.id),
                    ('employee_id', '=', record.employee_id.id),
                    ('state', 'in', ['draft', 'active']),
                    '|',
                    '&', ('date_from', '<=', record.date_to), ('date_to', '>=', record.date_from),
                    '&', ('date_from', '<=', record.date_from), ('date_to', '>=', record.date_to),
                ])
                if overlapping:
                    raise ValidationError(_(
                        'There is already an active delegation for %s during this period.'
                    ) % record.employee_id.name)
    
    @api.model
    def create(self, vals):
        delegation = super().create(vals)
        # Auto-activate if start date is today or in the past
        if delegation.date_from <= date.today() and delegation.state == 'draft':
            delegation.action_activate()
        return delegation
    
    def action_activate(self):
        """Activate delegation and apply it"""
        for record in self:
            record.state = 'active'
            record._apply_delegation()
        return True
    
    def action_cancel(self):
        """Cancel delegation and remove it"""
        for record in self:
            record.state = 'cancelled'
            record._remove_delegation()
        return True
    
    def action_expire(self):
        """Expire delegation and remove it"""
        for record in self:
            record.state = 'expired'
            record._remove_delegation()
        return True
    
    def _apply_delegation(self):
        """Apply delegation to CRM, Tasks, and Activities"""
        self.ensure_one()
        
        if not self.user_id or not self.delegate_to_user_id:
            return
        
        # Update CRM Opportunities - Reassign to delegated user
        exempted_stages = [
            'فرصة جديدة',
            'Won تمت الترسية',
            'new',' تم التقديم',
            'مراجعة الفرصة',
            'التواصل مع العميل',
            'دعم الأقسام الأخرى',
            'تجهيز العرض الفني والمالي',
            'بانتظار التعميد / التعديل'
        ]
        opportunities = self.env['crm.lead'].search([
            ('user_id', '=', self.user_id.id),
            ('type', '=', 'opportunity'),
            ('stage_id.name', 'in', exempted_stages),  # Exclude exempted stages
        ])
        # Reassign the opportunities to the delegated user
        if opportunities:
            opportunities.write({
                'user_id': self.delegate_to_user_id.id,
                'delegated_user_id': self.delegate_to_user_id.id
            })
            # Log the delegation for debugging
            _logger.info(f"Delegated {len(opportunities)} opportunities from {self.employee_id.name} to {self.delegate_to_employee_id.name}")
        else:
            _logger.info(f"No opportunities found to delegate for {self.employee_id.name}")
        # Add chatter message for each opportunity
        for opportunity in opportunities:
            opportunity.message_post(
                body=_('🔄 <strong>Employee Delegation Activated:</strong> This opportunity has been delegated from <strong>%s</strong> to <strong>%s</strong> due to employee delegation.') % (
                    self.employee_id.name, self.delegate_to_employee_id.name
                ),
                message_type='notification',
                subtype_xmlid='mail.mt_note'
            )
        
        # Update Project Tasks - Reassign to delegated user
        tasks = self.env['project.task'].search([
            ('user_ids', 'in', [self.user_id.id]),
            ('stage_id.fold', '=', False),  # Only active tasks
        ])
        # Reassign the tasks to the delegated user
        tasks.write({
            'user_ids': [(6, 0, [self.delegate_to_user_id.id])],
            'delegated_user_id': self.delegate_to_user_id.id
        })
        # Add chatter message for each task
        for task in tasks:
            task.message_post(
                body=_('🔄 <strong>Employee Delegation Activated:</strong> This task has been delegated from <strong>%s</strong> to <strong>%s</strong> due to employee delegation.') % (
                    self.employee_id.name, self.delegate_to_employee_id.name
                ),
                message_type='notification',
                subtype_xmlid='mail.mt_note'
            )
        
        # Update Activities - Reassign to delegated user
        activities = self.env['mail.activity'].search([
            ('user_id', '=', self.user_id.id),
            ('date_deadline', '>=', date.today()),  # Only future activities
        ])
        # Reassign the activities to the delegated user
        activities.write({
            'user_id': self.delegate_to_user_id.id,
            'delegated_user_id': self.delegate_to_user_id.id
        })
        # Note: Activities don't have chatter, but we can add a note to the related record
        for activity in activities:
            if activity.res_model and activity.res_id:
                try:
                    related_record = self.env[activity.res_model].browse(activity.res_id)
                    if hasattr(related_record, 'message_post'):
                        related_record.message_post(
                            body=_('🔄 <strong>Employee Delegation Activated:</strong> Activity "%s" has been delegated from <strong>%s</strong> to <strong>%s</strong> due to employee delegation.') % (
                                activity.summary or activity.activity_type_id.name,
                                self.employee_id.name, 
                                self.delegate_to_employee_id.name
                            ),
                            message_type='notification',
                            subtype_xmlid='mail.mt_note'
                        )
                except:
                    pass  # Skip if related record doesn't exist or doesn't support chatter
    
    def _remove_delegation(self):
        """Remove delegation from CRM, Tasks, and Activities - Reassign back to original user"""
        self.ensure_one()
        
        if not self.delegate_to_user_id or not self.user_id:
            return
        
        # Reassign CRM Opportunities back to original user
        opportunities = self.env['crm.lead'].search([
            ('delegated_user_id', '=', self.delegate_to_user_id.id),
            ('user_id', '=', self.delegate_to_user_id.id)
        ])
        opportunities.write({
            'user_id': self.user_id.id,
            'delegated_user_id': False
        })
        # Add chatter message for each opportunity
        for opportunity in opportunities:
            opportunity.message_post(
                body=_('↩️ <strong>Employee Delegation Ended:</strong> This opportunity has been returned from <strong>%s</strong> to <strong>%s</strong> due to delegation expiration/cancellation.') % (
                    self.delegate_to_employee_id.name, self.employee_id.name
                ),
                message_type='notification',
                subtype_xmlid='mail.mt_note'
            )
        
        # Reassign Project Tasks back to original user
        tasks = self.env['project.task'].search([
            ('delegated_user_id', '=', self.delegate_to_user_id.id)
        ])
        tasks.write({
            'user_ids': [(6, 0, [self.user_id.id])],
            'delegated_user_id': False
        })
        # Add chatter message for each task
        for task in tasks:
            task.message_post(
                body=_('↩️ <strong>Employee Delegation Ended:</strong> This task has been returned from <strong>%s</strong> to <strong>%s</strong> due to delegation expiration/cancellation.') % (
                    self.delegate_to_employee_id.name, self.employee_id.name
                ),
                message_type='notification',
                subtype_xmlid='mail.mt_note'
            )
        
        # Reassign Activities back to original user
        activities = self.env['mail.activity'].search([
            ('delegated_user_id', '=', self.delegate_to_user_id.id),
            ('user_id', '=', self.delegate_to_user_id.id)
        ])
        activities.write({
            'user_id': self.user_id.id,
            'delegated_user_id': False
        })
        # Add chatter message for related records of activities
        for activity in activities:
            if activity.res_model and activity.res_id:
                try:
                    related_record = self.env[activity.res_model].browse(activity.res_id)
                    if hasattr(related_record, 'message_post'):
                        related_record.message_post(
                            body=_('↩️ <strong>Employee Delegation Ended:</strong> Activity "%s" has been returned from <strong>%s</strong> to <strong>%s</strong> due to delegation expiration/cancellation.') % (
                                activity.summary or activity.activity_type_id.name,
                                self.delegate_to_employee_id.name,
                                self.employee_id.name
                            ),
                            message_type='notification',
                            subtype_xmlid='mail.mt_note'
                        )
                except:
                    pass  # Skip if related record doesn't exist or doesn't support chatter
    
    @api.model
    def cron_update_delegations(self):
        """
        Scheduled action to update delegations
        - Activate delegations that should start today
        - Expire delegations that ended
        """
        today = date.today()
        
        # Activate delegations starting today
        to_activate = self.search([
            ('state', '=', 'draft'),
            ('date_from', '<=', today),
        ])
        for delegation in to_activate:
            delegation.action_activate()
        
        # Expire delegations that ended
        to_expire = self.search([
            ('state', '=', 'active'),
            ('date_to', '<', today),
        ])
        for delegation in to_expire:
            delegation.action_expire()
        
        return True
    
    def action_view_delegated_opportunities(self):
        """Open delegated opportunities"""
        self.ensure_one()
        return {
            'name': _('Delegated Opportunities'),
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'view_mode': 'kanban,list,form',
            'domain': [('delegated_user_id', '=', self.delegate_to_user_id.id)],
            'context': {'default_user_id': self.user_id.id}
        }
    
    def action_view_delegated_tasks(self):
        """Open delegated tasks"""
        self.ensure_one()
        return {
            'name': _('Delegated Tasks'),
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'view_mode': 'kanban,list,form',
            'domain': [('delegated_user_id', '=', self.delegate_to_user_id.id)],
        }
    
    def action_view_delegated_activities(self):
        """Open delegated activities"""
        self.ensure_one()
        return {
            'name': _('Delegated Activities'),
            'type': 'ir.actions.act_window',
            'res_model': 'mail.activity',
            'view_mode': 'list,form',
            'domain': [('delegated_user_id', '=', self.delegate_to_user_id.id)],
        }

