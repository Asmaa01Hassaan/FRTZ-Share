{
    'name': 'CRM ↔ Project Task Link',
    'version': '1.0.0',
    'category': 'Custom',
    'author': 'Your Company',
    # 'depends': ['crm','base',
    #             'project',
    #             'web_grid',
    #             'web_hierarchy',
    #             'web_studio','sale', ],
    'depends': ['base', 'crm','website', 'project', 'hr_expense', 'account', 'sale','account_budget', 'laft_document_management'],

    'data': [
        'data/project_charter_sequence.xml',
        'security/groups.xml',
        'security/ir.model.access.csv',

        'report/project_charter_report.xml',

        'views/crm_lead_redesign_view.xml',
        'views/operational_expense_views.xml',
        'views/project_projectt_redesign_view.xml',
        'views/attachment_view.xml',
        'views/content_template.xml',
        'views/template_dashboard.xml',
        'views/portal_project_view.xml',
        'views/invoice_sale_template.xml',


    ],

    'assets': {
        'web.assets_backend': [
            'crm_task_link/static/src/css/project_form.css',
            'crm_task_link/static/src/css/crm_lead_form.css',
        ],
        'web.assets_frontend': [
            'crm_task_link/static/src/css/core.css',
        ],
    },
    'installable': True,
    'application': False,
    # 'post_init_hook': 'post_init_create_fields',
}
