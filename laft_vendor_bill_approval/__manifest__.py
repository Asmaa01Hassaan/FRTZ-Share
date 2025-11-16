# -*- coding: utf-8 -*-
{
    "name": "Vendor Bill Multi-stage Approval",
    "version": "18.0.1.0.0",
    "summary": "PM → BD → Finance approval workflow for vendor bills",
    "category": "Accounting/Accounting",
    "depends": ["account", "mail","crm_task_link"],
    "data": [
        "security/bill_approval_groups.xml",
        # "security/ir.model.access.csv",
        "data/mail_templates.xml",
        "views/account_move_views.xml",
        "views/account_move_search.xml",
    ],
    "license": "LGPL-3",
    "application": False,
}
