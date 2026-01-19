from odoo import fields, models, api


class ContactAttachment(models.Model):
    _name = 'contact.attachment'
    _description = 'Contact Attachment'
    _order = 'id desc'

    partner_id = fields.Many2one('res.partner', string='Partner', required=True, ondelete='cascade')
    attachment_id = fields.Many2one('ir.attachment', string='Attachment', ondelete='cascade')
    name = fields.Char(string='Attachment Name', required=True, help='Display name for this attachment')
    file = fields.Binary(string='Upload File', help='Upload a file to attach')
    filename = fields.Char(string='Filename', help='Name of the uploaded file')

    # Related fields from ir.attachment for easy display
    file_size = fields.Integer(string='File Size', related='attachment_id.file_size', readonly=True)
    mimetype = fields.Char(string='Mime Type', related='attachment_id.mimetype', readonly=True)
    datas = fields.Binary(string='File Content', related='attachment_id.datas', readonly=True)
    attachment_name = fields.Char(string='File Name', related='attachment_id.name', readonly=True, store=False)

    # Combined field for upload/download - shows datas when available, allows upload when not
    file_data = fields.Binary(
        string='File',
        compute='_compute_file_data',
        inverse='_inverse_file_data',
        store=False,
        help='Upload or download the attachment file'
    )

    # Computed filename for the binary field
    file_display_name = fields.Char(
        string='File Name',
        compute='_compute_file_display_name',
        store=False
    )

    @api.depends('attachment_id', 'attachment_id.name', 'name', 'filename')
    def _compute_file_display_name(self):
        """Return the appropriate filename for display"""
        for record in self:
            if record.attachment_id and record.attachment_id.name:
                record.file_display_name = record.attachment_id.name
            elif record.filename:
                record.file_display_name = record.filename
            else:
                record.file_display_name = record.name or 'Attachment'

    @api.depends('attachment_id', 'attachment_id.datas')
    def _compute_file_data(self):
        """Return attachment data for download"""
        for record in self:
            if record.attachment_id and record.attachment_id.datas:
                record.file_data = record.attachment_id.datas
            else:
                record.file_data = False

    def _inverse_file_data(self):
        """Handle file upload through file_data field - inverse is only called on upload, not download"""
        for record in self:
            if record.file_data:
                # New file uploaded, store in file field to trigger the create/write logic
                record.file = record.file_data
                record.filename = record.name or 'Attachment'

    @api.onchange('file')
    def _onchange_file(self):
        """Prepare attachment creation when file is uploaded (actual creation happens in create/write)"""
        # Don't create attachment in onchange - let create/write handle it
        # This ensures partner_id is properly set
        pass

    def write(self, vals):
        """Handle file upload on write"""
        # Store file data temporarily
        file_data = vals.pop('file', False)
        filename = vals.pop('filename', False)

        # Write other fields first
        result = super().write(vals)

        # If file was uploaded, create or update attachment
        if file_data:
            partner_id = self.partner_id.id if self.partner_id else False
            attachment_name = filename or self.name or 'Attachment'

            # If there's an existing attachment, update it; otherwise create a new one
            if self.attachment_id:
                self.attachment_id.write({
                    'name': attachment_name,
                    'datas': file_data,
                })
            else:
                attachment = self.env['ir.attachment'].create({
                    'name': attachment_name,
                    'type': 'binary',
                    'datas': file_data,
                    'res_model': 'res.partner',
                    'res_id': partner_id,
                })
                self.attachment_id = attachment.id

        return result

    @api.model
    def create(self, vals):
        """Handle file upload on create"""
        # Store file data temporarily
        file_data = vals.pop('file', False)
        filename = vals.pop('filename', False)

        # Create the record first to get the partner_id
        record = super().create(vals)

        # If file was uploaded, create attachment now that we have partner_id
        if file_data:
            attachment = self.env['ir.attachment'].create({
                'name': filename or record.name or 'Attachment',
                'type': 'binary',
                'datas': file_data,
                'res_model': 'res.partner',
                'res_id': record.partner_id.id if record.partner_id else False,
            })
            record.attachment_id = attachment.id

        return record

