from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    uid = fields.Char(string="UID")
    use_name_parts = fields.Boolean(string="Use Name Details", default=False,
                                    help="Enable this to compose the name from individual name parts. "
                                         "When enabled, the name field becomes read-only and is automatically updated from the name parts.")
    first_name = fields.Char(string="First Name")
    father_name = fields.Char(string="Father Name")
    gfather_name = fields.Char(string="GFather Name")
    sur_name = fields.Char(string="Sur Name")
    birth_date = fields.Date(string="Birth Date")
    hiring_date = fields.Date(string="Hiring Date")
    name_from_parts = fields.Boolean(compute="_compute_name_from_parts", store=False)
    status = fields.Selection([
        ('active', 'Active'),
        ('suspended', 'Suspended'),
    ], string='Status', default='active')
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    division_ids = fields.One2many("contact.division", "partner_id", string="Divisions")
    divisions = fields.Many2one(
        "contact.division",
        string="Department",
        help="For individuals, select a department from the related company divisions.",
        domain="[('partner_id', '=', parent_id)]",
    )
    contact_address_ids = fields.One2many('contact.addresses', 'partner_id', string='Contact Addresses')
    attachment_ids = fields.One2many('contact.attachment', 'partner_id', string='Attachments')
    channel_ids = fields.One2many('contact.channels', 'partner_id', string='Channels')
    max_salary_deduction = fields.Monetary(string='Max Salary Deduction', currency_field='currency_id')
    max_installments_amount = fields.Monetary(string='Max Installments Amount', currency_field='currency_id')
    max_grantees_amount = fields.Monetary(string='Max Grantees Amount', currency_field='currency_id')

    @api.depends('use_name_parts', 'first_name', 'father_name', 'gfather_name', 'sur_name')
    def _compute_name_from_parts(self):
        """Compute if name should be readonly based on use_name_parts checkbox"""
        for record in self:
            record.name_from_parts = record.use_name_parts

    @api.depends('name', 'ref')
    def _compute_display_name(self):
        """Compute display name with ref prefix"""
        for partner in self:
            name = partner.name or ''
            if partner.ref:
                name = f"{partner.ref} {name}"
            partner.display_name = name

    @api.onchange('use_name_parts')
    def _onchange_use_name_parts(self):
        """Handle checkbox change - clear name parts if unchecked"""
        if not self.use_name_parts:
            # Clear all name parts when checkbox is unchecked
            self.first_name = False
            self.father_name = False
            self.gfather_name = False
            self.sur_name = False
        elif self.use_name_parts:
            # If checked and name parts exist, update name
            self._onchange_name_parts()

    @api.onchange('first_name', 'father_name', 'gfather_name', 'sur_name')
    def _onchange_name_parts(self):
        """Automatically update name field when name parts are entered (only if use_name_parts is True)"""
        if not self.use_name_parts:
            return
        
        name_parts = []
        if self.first_name:
            name_parts.append(self.first_name)
        if self.father_name:
            name_parts.append(self.father_name)
        if self.gfather_name:
            name_parts.append(self.gfather_name)
        if self.sur_name:
            name_parts.append(self.sur_name)
        
        if name_parts:
            self.name = ' '.join(name_parts)

    @api.onchange('channel_ids')
    def _onchange_channel_ids_sync_defaults(self):
        """Sync default channel values to partner phone/mobile/email fields"""
        default_channels = self.channel_ids.filtered(lambda c: c.is_default and c.status)
        
        for channel in default_channels:
            if channel.channel == 'phone':
                self.phone = channel.value
            elif channel.channel == 'mobile':
                self.mobile = channel.value
            elif channel.channel == 'email':
                self.email = channel.value

    @api.onchange('contact_address_ids')
    def _onchange_contact_address_ids_set_default_address(self):
        """
        When the default address is changed in the one2many, reflect it on the main
        partner address fields (street/city/state/zip/country).

        Also make sure there is at most one default address in the one2many to avoid
        ambiguity.
        """
        # Determine which line should be considered "the" default.
        defaults = self.contact_address_ids.filtered(lambda l: l.is_default)
        if not defaults:
            return

        # Prefer the most recently created/edited line as the default if multiple are checked.
        default_line = defaults[-1]

        # Enforce single default in memory (onchange)
        for line in (defaults - default_line):
            line.is_default = False

        # Copy address values to main partner address fields.
        self.street = default_line.street
        self.street2 = default_line.street2
        self.city = default_line.city
        self.state_id = default_line.state_id
        self.zip = default_line.zip
        self.country_id = default_line.country_id

    @api.onchange("parent_id")
    def _onchange_parent_id_set_department(self):
        """
        For individuals: when a company is set, keep department (divisions) consistent.
        If the company has only one division, auto-select it.
        """
        if self.is_company:
            return

        if not self.parent_id:
            self.divisions = False
            return

        # Clear if it doesn't belong to the selected company
        if self.divisions and self.divisions.partner_id != self.parent_id:
            self.divisions = False

        # Auto-pick if exactly one division exists
        division_list = self.parent_id.division_ids
        if not self.divisions and len(division_list) == 1:
            self.divisions = division_list[0]

    def write(self, vals):
        """Clear name parts when use_name_parts is unchecked and prevent manual name editing when checked"""
        # If use_name_parts is being set to False, clear all name parts
        if 'use_name_parts' in vals and not vals['use_name_parts']:
            vals['first_name'] = False
            vals['father_name'] = False
            vals['gfather_name'] = False
            vals['sur_name'] = False
        
        # Prevent manual name editing when use_name_parts is True
        # Only allow name changes if it's coming from name parts update
        for record in self:
            if record.use_name_parts and 'name' in vals:
                # Check if name parts are being updated (which will update name via onchange)
                if not any(key in vals for key in ['first_name', 'father_name', 'gfather_name', 'sur_name']):
                    # If name is being changed manually without name parts update, ignore it
                    # Recompute name from current name parts instead
                    name_parts = []
                    first_name = vals.get('first_name', record.first_name)
                    father_name = vals.get('father_name', record.father_name)
                    gfather_name = vals.get('gfather_name', record.gfather_name)
                    sur_name = vals.get('sur_name', record.sur_name)
                    
                    if first_name:
                        name_parts.append(first_name)
                    if father_name:
                        name_parts.append(father_name)
                    if gfather_name:
                        name_parts.append(gfather_name)
                    if sur_name:
                        name_parts.append(sur_name)
                    
                    if name_parts:
                        vals['name'] = ' '.join(name_parts)
                    else:
                        # If no name parts, keep existing name or remove the name change
                        del vals['name']
        
        result = super().write(vals)
        
        # Also clear name parts for records where use_name_parts is False
        for record in self:
            if not record.use_name_parts and (record.first_name or record.father_name or 
                                               record.gfather_name or record.sur_name):
                record.write({
                    'first_name': False,
                    'father_name': False,
                    'gfather_name': False,
                    'sur_name': False,
                })
        
        return result

    def name_get(self):
        """Override name_get to use display_name"""
        result = []
        for partner in self:
            result.append((partner.id, partner.display_name or partner.name))
        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """
        Override name_search to include ref in search
        """
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', 'ilike', name), ('ref', 'ilike', name)]
        records = self.search(domain + args, limit=limit)
        return records.name_get()

