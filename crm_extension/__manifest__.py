{
    'name': 'CRM Extension',
    'version': '1.0.0',
    'category': '',
    'author': 'Omar Radwan',

    'depends':['base','crm','product','analytic',
               'project','sale_management','account','purchase','mail'
               ],
    'data': [
            'security/ir.model.access.csv',
            'views/crm_extension.xml',
            'views/crm_lead_line.xml',
            'views/project_proposal_view.xml',
            'views/proposal_stages_view.xml',
            'views/proposal_loss_reason_view.xml',
            'views/proposal_line_view.xml',
            'wizard/lost_reason__wizard_view.xml',
            'data/ir_sequance.xml'
    ],

    'installable': True,
    'application': True,
    # 'post_init_hook': 'post_init_create_fields',
}
