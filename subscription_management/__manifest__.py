# -*- coding: utf-8 -*-
{
    'name': 'Subscription Management',
    'version': '18.0.1.0.0',
    'category': 'Sales/Subscription',
    'summary': 'Hybrid subscription orders (one-time + recurring), ad-hoc charges, '
               'automated/manual recurring billing, and order/line lifecycle states',
    'description': """
Subscription Management
=======================

A self-contained subscription engine built on standard Sales + Accounting.
It is INDEPENDENT of sttl_sale_subscription (different models/fields).

Implements the documented requirements:

* Hybrid order identity: a single subscription order can mix one-time lines
  (setup fee, SIM card) and recurring lines (monthly/yearly package).
* Ad-hoc charges: variable, unscheduled amounts added to the next invoice
  (e.g. excess international calls, temporary extra internet package).
* Automated billing: a daily Cron generates invoices for due subscriptions.
* Manual billing: a button issues / accelerates the invoice on demand.
* Lifecycle on two levels:
    - Order level: Pending / Active / Suspended (temporary) / Cancelled
      (permanent) / Closed (term reached).
    - Line level: Active / Paused (item-level pause) - the billing engine
      skips paused lines while billing the rest of the subscription.
* Provisioning signal hook (_post_provisioning_signal) for service
  activation / suspension / disconnection, ready to integrate with an OSS.
""",
    'author': 'FRTZ',
    'website': 'https://frtz.com',
    # sales_order_extension provides sale.order.type + order_classification,
    # which drives `is_subscription` (choosing a Subscription-classified order
    # type switches the order onto this engine).
    # pricelist_expression is listed so this module loads AFTER it: pricelist_expression
    # recomputes line prices from the pricelist on create/write, and the per-period
    # subscription price must take precedence over that for recurring lines.
    # product_extension provides the `subscription_ok` flag on products (the
    # single "Subscription" checkbox); this module reuses it instead of adding a
    # second flag.
    'depends': [
        'sale_management', 'account', 'product',
        'sales_order_extension', 'pricelist_expression', 'product_extension',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'data/subscription_reason_data.xml',
        'wizard/subscription_invoice_wizard_views.xml',
        'wizard/subscription_control_wizards_views.xml',
        'views/subscription_period_views.xml',
        'views/product_views.xml',
        'views/subscription_control_views.xml',
        'views/sale_order_views.xml',
        'views/subscription_menus.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}
