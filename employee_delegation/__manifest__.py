{
    'name': 'Employee Delegation Management',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Manage employee delegations for vacations and resignations',
    'description': """
        Employee Delegation Management
        ===============================
        
        Professional delegation system for managing employee absences:
        
        **Key Features:**
        * Delegate CRM opportunities to other users
        * Delegate project tasks to other users
        * Delegate activities to other users
        * Automatic delegation based on date ranges
        * Visual indicators in Kanban and List views
        * No impact on original ownership
        * Automatic expiration of delegations
        
        **Use Cases:**
        * Employee vacations
        * Employee resignations
        * Temporary coverage
        * Workload distribution
        
        **Technical Implementation:**
        * New delegation model (hr.employee.delegation)
        * Extended CRM, Projects, and Activities models
        * Automated cron job for delegation updates
        * Custom record rules for access control
        * Enhanced UI with delegation badges
    """,
    'author': 'Laft Company',
    'website': 'https://laft.com.sa',
    'depends': [
        'base',
        'hr',
        'crm',
        'project',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/cron_data.xml',
        'views/hr_employee_delegation_views.xml',
        'views/hr_employee_views.xml',
        # 'views/my_profile_views.xml',  # Temporarily disabled
        'views/crm_lead_views.xml',
        'views/project_task_views.xml',
        'views/mail_activity_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}

