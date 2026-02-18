from odoo import api, fields, models


class CrmExtension(models.Model):
    _name = 'crm.extension'


    name = fields.Char(string='Name')