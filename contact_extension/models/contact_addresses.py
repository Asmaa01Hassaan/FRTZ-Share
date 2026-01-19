from odoo import fields, models, api


class ContactAddresses(models.Model):
    _name = 'contact.addresses'
    _description = 'Contact Addresses'
    _order = 'id desc'

    partner_id = fields.Many2one('res.partner', string='Contact', required=True, ondelete='cascade')
    type = fields.Selection([
        ('contact', 'Address'),
        ('invoice', 'Invoice Address'),
        ('delivery', 'Delivery Address'),
        ('other', 'Other'),
    ], string='Address Type', default='contact', required=True)
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street2')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string='State', 
                               domain="[('country_id', '=', country_id)]")
    zip = fields.Char(string='ZIP')
    country_id = fields.Many2one('res.country', string='Country')
    name = fields.Char(string='Address Name', help='Name or description for this address')
    is_default = fields.Boolean(string='Default Address', default=False)

    @api.onchange('is_default')
    def _onchange_is_default(self):
        """
        UX helper: when marking a line as default inside the one2many,
        unmark other default lines of the same partner in-memory.
        The actual syncing to res.partner fields is done in res.partner onchange.
        """
        if not self.is_default:
            return
        siblings = self.partner_id.contact_address_ids.filtered(lambda l: l != self and l.is_default)
        for line in siblings:
            line.is_default = False

    @api.onchange('country_id')
    def _onchange_country_id(self):
        if self.country_id and self.country_id.state_ids:
            if len(self.country_id.state_ids) == 1:
                self.state_id = self.country_id.state_ids[0]
        else:
            self.state_id = False

    def name_get(self):
        result = []
        for record in self:
            name_parts = []
            if record.name:
                name_parts.append(record.name)
            elif record.street:
                name_parts.append(record.street)
            else:
                name_parts.append(f"Address #{record.id}")
            
            if record.city:
                name_parts.append(f"- {record.city}")
            
            result.append((record.id, ' '.join(name_parts)))
        return result

