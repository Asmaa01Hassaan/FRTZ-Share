{
    "name": "Purchase: CEO Approval",
    'description': """This module adds a CEO approval state to purchase orders.""",
    "version": "18.0.1.0",
    'category': 'Purchases',
    'sequence': 1,
    "depends": ["purchase", "mail","crm_task_link"],
    "data": [
        "security/ceo_groups.xml",
        "security/ir.model.access.csv",
        "views/purchase_order_views.xml",
    ],
    "license": "LGPL-3",
    'application': True,
    "installable": True,
}
