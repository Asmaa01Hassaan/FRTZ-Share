# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ResUsers(models.Model):
    _inherit = 'res.users'
    
    # ========================================
    # SIMPLIFIED PERMISSION FIELDS
    # ========================================
    
    # Project Access
    laft_project_access = fields.Selection([
        ('none', 'No Access'),
        ('user', 'User - Own Projects Only'),
        ('manager', 'Manager - Own Projects'),
        ('finance', 'Manager + Finance'),
        ('general', 'General Manager - All Projects')
    ], string='Project Access Level', default='none',
       help="Determines what projects the user can see and manage")
    
    laft_project_see_all = fields.Boolean(
        string='Override: See All Projects',
        help="Allow user to see ALL projects regardless of ownership"
    )
    
    # Project Capabilities
    laft_can_create_projects = fields.Boolean('Can Create Projects', default=False)
    laft_can_manage_tasks = fields.Boolean('Can Manage Tasks', default=True)
    laft_can_view_bills = fields.Boolean('Can View Vendor Bills (Project)', default=False)
    laft_can_create_bills = fields.Boolean('Can Create Vendor Bills (Project)', default=False)
    laft_can_view_pos = fields.Boolean('Can View Purchase Orders (Project)', default=False)
    laft_can_create_pos = fields.Boolean('Can Create Purchase Orders (Project)', default=False)
    laft_can_approve_bills = fields.Boolean('Can Approve Bills', default=False)
    
    # Business Development Access
    laft_bd_access = fields.Selection([
        ('none', 'No Access'),
        ('user', 'User - Own Opportunities'),
        ('manager', 'Manager - Team'),
        ('executive', 'Executive - All')
    ], string='BD Access Level', default='none',
       help="Determines what CRM opportunities the user can see")
    
    # Finance Access
    laft_finance_access = fields.Selection([
        ('none', 'No Access'),
        ('project_only', 'Project-Related Only'),
        ('bills_approval', 'Bills Approval'),
        ('invoicing', 'Full Invoicing'),
        ('accounting', 'Full Accounting')
    ], string='Finance Access Level', default='none')
    
    # Administration
    laft_is_admin = fields.Boolean('System Administrator', default=False)
    laft_can_manage_permissions = fields.Boolean('Can Manage User Permissions', default=False)
    
    # Dashboard Access
    laft_dashboard_my = fields.Boolean('My Personal Dashboard', default=True)
    laft_dashboard_projects = fields.Boolean('Projects Dashboard', default=False)
    laft_dashboard_bd = fields.Boolean('BD Dashboard', default=False)
    laft_dashboard_executive = fields.Boolean('Executive Dashboard', default=False)
    
    # Technical - Computed field to show applied groups
    laft_applied_groups = fields.Text(
        string='Applied Groups',
        compute='_compute_applied_groups',
        help="Technical field showing which groups are currently applied"
    )
    
    # ========================================
    # COMPUTED FIELDS
    # ========================================
    
    @api.depends('groups_id')
    def _compute_applied_groups(self):
        """Show which groups are currently applied to this user"""
        for user in self:
            groups = user.groups_id.filtered(
                lambda g: g.category_id.name in [
                    'Project', 'Sales', 'Invoicing', 'Laft Permissions'
                ]
            )
            user.laft_applied_groups = '\n'.join(
                f"• {g.full_name}" for g in groups.sorted('full_name')
            )
    
    # ========================================
    # ONCHANGE METHODS - Auto-apply groups
    # ========================================
    
    @api.onchange('laft_project_access')
    def _onchange_project_access(self):
        """Auto-apply groups when project access level changes"""
        if not self.laft_project_access or self.laft_project_access == 'none':
            return
        
        # Remove old project groups first
        self._remove_project_groups()
        
        # Apply new groups based on level
        if self.laft_project_access == 'user':
            # Add base Odoo group
            self._add_group('project.group_project_user')
            # Add custom group
            self._add_group('laft_advanced_permissions.group_project_user_own')
            self.laft_can_create_projects = False
            self.laft_can_view_bills = False
            self.laft_can_create_bills = False
            
        elif self.laft_project_access == 'manager':
            # Add base Odoo group
            self._add_group('project.group_project_manager')
            # Add custom group
            self._add_group('laft_advanced_permissions.group_project_manager_own')
            self.laft_can_create_projects = True
            self.laft_can_manage_tasks = True
            
        elif self.laft_project_access == 'finance':
            # Add base Odoo groups
            self._add_group('project.group_project_manager')
            # Add custom group
            self._add_group('laft_advanced_permissions.group_project_manager_finance')
            self.laft_can_create_projects = True
            self.laft_can_view_bills = True
            self.laft_can_create_bills = True
            self.laft_can_view_pos = True
            self.laft_can_create_pos = True
            
        elif self.laft_project_access == 'general':
            # Add base Odoo groups
            self._add_group('project.group_project_manager')
            # Add custom group
            self._add_group('laft_advanced_permissions.group_project_general_manager')
            self.laft_project_see_all = True
            self.laft_can_create_projects = True
            self.laft_can_view_bills = True
            self.laft_can_create_bills = True
            self.laft_can_approve_bills = True
    
    @api.onchange('laft_bd_access')
    def _onchange_bd_access(self):
        """Auto-apply groups when BD access level changes"""
        if not self.laft_bd_access or self.laft_bd_access == 'none':
            return
        
        # Remove old BD groups
        self._remove_bd_groups()
        
        # Apply new groups
        if self.laft_bd_access == 'user':
            # Add base Odoo group
            self._add_group('sales_team.group_sale_salesman')
            # Add custom group
            self._add_group('laft_advanced_permissions.group_bd_user_own')
            
        elif self.laft_bd_access == 'manager':
            # Add base Odoo group
            self._add_group('sales_team.group_sale_salesman')
            # Add custom group
            self._add_group('laft_advanced_permissions.group_bd_manager_team')
            
        elif self.laft_bd_access == 'executive':
            # Add base Odoo group
            self._add_group('sales_team.group_sale_manager')
            # Add custom group
            self._add_group('laft_advanced_permissions.group_bd_executive')
    
    @api.onchange('laft_project_see_all')
    def _onchange_project_see_all(self):
        """Override to see all projects"""
        if self.laft_project_see_all:
            self._add_group('laft_advanced_permissions.group_project_general_manager')
        else:
            self._remove_group('laft_advanced_permissions.group_project_general_manager')
    
    @api.onchange('laft_is_admin')
    def _onchange_is_admin(self):
        """Make user system administrator"""
        if self.laft_is_admin:
            self._add_group('base.group_system')
        else:
            self._remove_group('base.group_system')
    
    @api.onchange('laft_can_manage_permissions')
    def _onchange_can_manage_permissions(self):
        """Allow user to manage permissions"""
        if self.laft_can_manage_permissions:
            self._add_group('laft_advanced_permissions.group_permission_manager')
        else:
            self._remove_group('laft_advanced_permissions.group_permission_manager')
    
    @api.onchange('laft_can_approve_bills')
    def _onchange_can_approve_bills(self):
        """Add bill approval group"""
        if self.laft_can_approve_bills:
            self._add_group('laft_vendor_bill_approval.group_bill_pm')
        else:
            self._remove_group('laft_vendor_bill_approval.group_bill_pm')
    
    @api.onchange('laft_dashboard_projects')
    def _onchange_dashboard_projects(self):
        """Add projects dashboard group"""
        if self.laft_dashboard_projects:
            self._add_group('executive_dashboard_v2.group_projects_dashboard_user')
        else:
            self._remove_group('executive_dashboard_v2.group_projects_dashboard_user')
    
    @api.onchange('laft_dashboard_bd')
    def _onchange_dashboard_bd(self):
        """Add BD dashboard group"""
        if self.laft_dashboard_bd:
            self._add_group('executive_dashboard_v2.group_bd_dashboard_user')
        else:
            self._remove_group('executive_dashboard_v2.group_bd_dashboard_user')
    
    # ========================================
    # HELPER METHODS
    # ========================================
    
    def _add_group(self, xml_id):
        """Helper to add a group by XML ID"""
        try:
            group = self.env.ref(xml_id)
            self.groups_id = [(4, group.id)]
        except:
            pass
    
    def _remove_group(self, xml_id):
        """Helper to remove a group by XML ID"""
        try:
            group = self.env.ref(xml_id)
            self.groups_id = [(3, group.id)]
        except:
            pass
    
    def _remove_project_groups(self):
        """Remove all project-related groups"""
        project_groups = [
            'laft_advanced_permissions.group_project_user_own',
            'laft_advanced_permissions.group_project_manager_own',
            'laft_advanced_permissions.group_project_manager_finance',
        ]
        for xml_id in project_groups:
            self._remove_group(xml_id)
    
    def _remove_bd_groups(self):
        """Remove all BD-related groups"""
        bd_groups = [
            'laft_advanced_permissions.group_bd_user_own',
            'laft_advanced_permissions.group_bd_manager_team',
        ]
        for xml_id in bd_groups:
            self._remove_group(xml_id)
    
    # ========================================
    # WRITE METHOD - Apply on save
    # ========================================
    
    def write(self, vals):
        """Apply group changes when saving"""
        result = super(ResUsers, self).write(vals)
        
        # Trigger onchange logic on write
        for user in self:
            if 'laft_project_access' in vals:
                user._onchange_project_access()
            if 'laft_bd_access' in vals:
                user._onchange_bd_access()
            if 'laft_project_see_all' in vals:
                user._onchange_project_see_all()
        
        return result

