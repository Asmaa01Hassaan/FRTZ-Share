{
    'name': 'Laft Advanced Permissions System',
    'version': '1.0.0',
    'category': 'Administration',
    'summary': 'Advanced permission management system for Laft Company',
    'description': """
        Laft Advanced Permissions
        =========================
        
        Professional permission management system with:
        
        **Key Features:**
        * Simplified user interface for permission management
        * Role-based access control (RBAC)
        * Granular project access (Own vs All)
        * Permission dashboard and audit trail
        * Pre-configured role templates
        
        **Project Access Levels:**
        * User - Own projects only
        * Manager - Full access to own projects
        * Manager + Finance - Projects + Bills/POs
        * General Manager - See ALL projects
        
        **Business Development Access:**
        * User - Own opportunities
        * Manager - Team opportunities
        * Executive - All opportunities
        
        **User-Friendly Interface:**
        * Simple checkboxes instead of complex groups
        * Permission dashboard showing who has what
        * Quick role assignment templates
        * Audit log for changes
    """,
    'author': 'Laft Company',
    'website': 'https://laft.com.sa',
    'depends': [
        'base',
        'project',
        'crm',
        'sales_team',
        'account',
        'purchase',
        'hr',
        'mail',
        'laft_vendor_bill_approval',
        'executive_dashboard_v2',
    ],
    'data': [
        # Security - Groups must be loaded FIRST
        'security/laft_security_groups.xml',
        'security/project_security_rules.xml',
        'security/bd_security_rules.xml',
        'security/finance_security_rules.xml',
        
        # Data
        'data/default_roles_data.xml',
        
        # Views
        'views/res_users_permission_views.xml',
        'views/laft_permission_role_views.xml',
        'views/permission_dashboard_views.xml',
        'views/menu_views.xml',
        
        # Access rights - loaded last (XML format instead of CSV)
        'security/ir_model_access.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'laft_advanced_permissions/static/src/css/permissions_ui.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}

