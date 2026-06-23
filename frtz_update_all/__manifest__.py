# -*- coding: utf-8 -*-
{
    "name": "FRTZ Suite (meta / update-all)",
    "version": "18.0.1.0.0",
    "summary": "Umbrella module that groups the full FRTZ custom suite (13 modules).",
    "description": """
FRTZ Suite — one place that lists the whole custom stack.
==========================================================

WHAT THIS IS
------------
A dependency-only "meta" module. It has NO models, NO data and NO migrations,
so installing/upgrading it can never touch your business data. Its only content
is the dependency list below, which is the canonical definition of
"the FRTZ suite = these 13 modules".

INSTALL the whole suite on a FRESH database (one command, correct order):
    ./odoo-bin -c odoo.conf -d <DB> --stop-after-init -i frtz_update_all

UPGRADE the whole suite on an EXISTING database
-----------------------------------------------
IMPORTANT: `-u frtz_update_all` does NOT upgrade the 13 modules. In Odoo, `-u X`
upgrades X and everything that DEPENDS ON X (its dependents) - never X's own
dependencies. This meta-module sits on TOP of the 13, so it has no dependents.
(Source: odoo/addons/base/models/ir_module.py button_upgrade; odoo/modules/loading.py.)

To upgrade the suite, name the modules themselves. The ORDER does not matter -
Odoo always loads them in dependency order automatically:

    ./odoo-bin -c odoo.conf -d <DB> --stop-after-init -u \\
    contact_extension,access_roles,account_invoice_installments,\\
    installment_management_pro,installment_payment_extension,inventory_extension,\\
    invoice_installment_management,payment_term_installment_extension,\\
    pricelist_expression,product_extension,sales_order_extension,frtz_l10n,\\
    subscription_management

Shorter equivalent (Odoo's dependents-cascade expands these 6 to all 13):
    ... -u payment_term_installment_extension,product_extension,\\
    contact_extension,access_roles,inventory_extension,frtz_l10n

Or just use the helper script: tools/frtz_update.sh <DB>
""",
    "author": "FRTZ",
    "website": "",
    "license": "LGPL-3",
    "category": "Hidden",
    "depends": [
        "contact_extension",
        "access_roles",
        "account_invoice_installments",
        "installment_management_pro",
        "installment_payment_extension",
        "inventory_extension",
        "invoice_installment_management",
        "payment_term_installment_extension",
        "pricelist_expression",
        "product_extension",
        "sales_order_extension",
        "frtz_l10n",
        "subscription_management",
    ],
    "data": [
        "data/upgrade_suite_action.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
