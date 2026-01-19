from odoo import fields, models, api
from odoo.exceptions import ValidationError


class ContactChannels(models.Model):
    _name = 'contact.channels'
    _description = 'Contact Channels'
    _order = 'id desc'

    partner_id = fields.Many2one('res.partner', string='Partner', required=True, ondelete='cascade')
    type = fields.Char(string='Type', help='Label or type for this channel')
    channel = fields.Selection([
        ('phone', 'Phone'),
        ('mobile', 'Mobile'),
        ('whatsapp', 'WhatsApp'),
        ('facebook_messenger', 'Facebook Messenger'),
        ('email', 'Email'),
    ], string='Channel', required=True)
    value = fields.Char(string='Value', required=True, help='Contact value for this channel')
    status = fields.Boolean(string='Status', default=True, help='Active/Inactive status')
    is_default = fields.Boolean(string='Default', default=False, help='Mark as default channel')

    @api.onchange('is_default', 'channel', 'value', 'status')
    def _onchange_channel_fields(self):
        """Ensure only one default channel per partner and sync to partner fields"""
        if self.is_default and self.status and self.value:
            # In onchange context, we can't write to other records, so we'll handle it in write/create
            # But we can sync to the partner field directly
            self._sync_default_to_partner_onchange()
    
    def _sync_default_to_partner(self):
        """Sync default channel value to corresponding partner field"""
        if not self.is_default or not self.status or not self.partner_id or not self.value:
            return
        
        channel_mapping = {
            'phone': 'phone',
            'mobile': 'mobile',
            'email': 'email',
        }
        
        partner_field = channel_mapping.get(self.channel)
        if partner_field:
            self.partner_id.write({partner_field: self.value})
    
    def _sync_default_to_partner_onchange(self):
        """Sync default channel value to corresponding partner field (for onchange context)"""
        if not self.is_default or not self.status or not self.value:
            return
        
        channel_mapping = {
            'phone': 'phone',
            'mobile': 'mobile',
            'email': 'email',
        }
        
        partner_field = channel_mapping.get(self.channel)
        if partner_field and self.partner_id:
            # In onchange, we can directly assign to the partner
            setattr(self.partner_id, partner_field, self.value)
    
    @api.model
    def create(self, vals):
        """Handle default channel sync on create"""
        record = super().create(vals)
        if record.is_default:
            record._sync_default_to_partner()
        return record
    
    @api.constrains('is_default', 'status', 'partner_id')
    def _check_single_default(self):
        """Ensure only one default channel per partner"""
        for record in self:
            if record.is_default and record.status:
                other_defaults = record.partner_id.channel_ids.filtered(
                    lambda c: c.is_default and c.status and c.id != record.id
                )
                if other_defaults:
                    raise ValidationError(
                        'Only one default channel is allowed per partner. '
                        'Please uncheck the other default channel first.'
                    )
    
    def write(self, vals):
        """Handle default channel sync on write"""
        # If is_default is being set to True, uncheck others first
        if 'is_default' in vals and vals['is_default']:
            for record in self:
                other_defaults = record.partner_id.channel_ids.filtered(
                    lambda c: c.is_default and c.id != record.id
                )
                if other_defaults:
                    other_defaults.write({'is_default': False})
        
        result = super().write(vals)
        
        # After write, sync default channels to partner fields
        for record in self:
            if record.is_default and record.status:
                record._sync_default_to_partner()
        
        return result

