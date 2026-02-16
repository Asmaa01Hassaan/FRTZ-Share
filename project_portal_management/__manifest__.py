{
    'name': 'CRM ↔ Project Task Link',
    'version': '1.0.0',
    'category': 'Custom',
    'author': 'Your Company',

    'depends': ['base','website', 'project'],

    'data': [
        'views/content_template.xml',
        'views/template_dashboard.xml',
        'views/portal_project_view.xml',
        'views/invoice_template.xml',
        'views/sale_template.xml',


    ],

    'assets': {
        'web.assets_frontend': [
            'crm_task_link/static/src/css/core.css',
        ],
    },
    'installable': True,
    'application': False,
}
