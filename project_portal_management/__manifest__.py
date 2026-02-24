{
    'name': 'Project Portal Management',
    'version': '1.0.0',
    'category': 'Custom',
    'author': 'Your Company',

    'depends': ['base','website', 'project','crm_task_link'],

    'data': [
        'views/content_template.xml',
        'views/template_dashboard.xml',
        'views/portal_project_view.xml',
        'views/invoice_template.xml',
        'views/sale_template.xml',
        'views/website_layout.xml',
    ],

    'assets': {
        'web.assets_frontend': [
            'crm_task_link/static/src/css/core.css',
        ],
    },
    'installable': True,
    'application': False,
}
