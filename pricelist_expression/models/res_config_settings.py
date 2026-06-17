# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.tools.misc import str2bool


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    show_invoice_pricelist = fields.Boolean(
        string='Show in Customer Invoice',
        config_parameter='pricelist_expression.show_invoice_pricelist',
        help='Show a pricelist field on customer invoices and use it to compute invoice line prices.',
    )

    def get_values(self):
        res = super().get_values()
        ICP = self.env['ir.config_parameter'].sudo()
        value = ICP.get_param('pricelist_expression.show_invoice_pricelist', default=False)
        if value is False:
            value = ICP.get_param(
                'payment_term_installment_extension.show_invoice_pricelist',
                default='False',
            )
        res['show_invoice_pricelist'] = str2bool(value, default=False)
        return res
