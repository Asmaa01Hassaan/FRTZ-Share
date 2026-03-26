from odoo import api, fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'


    commercial_registration_number = fields.Char(string="Commercial Registration")