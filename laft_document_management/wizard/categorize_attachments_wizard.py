# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CategorizeAttachmentsWizard(models.TransientModel):
    _name = 'categorize.attachments.wizard'
    _description = 'ربط وتصنيف الملفات الموجودة'

    model_type = fields.Selection([
        ('crm.lead', 'فرص CRM'),
        ('project.project', 'المشاريع'),
        ('both', 'كلاهما'),
    ], string='نوع السجل', default='both', required=True)
    
    default_category_id = fields.Many2one(
        'document.category',
        string='التصنيف الافتراضي',
        default=lambda self: self.env.ref(
            'laft_document_management.category_general',
            raise_if_not_found=False
        ),
        required=True
    )
    
    attachment_count = fields.Integer(
        string='عدد الملفات',
        compute='_compute_attachment_count'
    )
    
    @api.depends('model_type')
    def _compute_attachment_count(self):
        for wizard in self:
            domain = [
                ('document_category_id', '=', False),
            ]
            
            if wizard.model_type == 'crm.lead':
                domain.append(('res_model', '=', 'crm.lead'))
            elif wizard.model_type == 'project.project':
                domain.append(('res_model', '=', 'project.project'))
            elif wizard.model_type == 'both':
                domain.append(('res_model', 'in', ['crm.lead', 'project.project']))
            
            wizard.attachment_count = self.env['ir.attachment'].search_count(domain)
    
    def action_categorize(self):
        """ربط الملفات الموجودة بالتصنيف المحدد"""
        self.ensure_one()
        
        domain = [
            ('document_category_id', '=', False),
        ]
        
        if self.model_type == 'crm.lead':
            domain.append(('res_model', '=', 'crm.lead'))
        elif self.model_type == 'project.project':
            domain.append(('res_model', '=', 'project.project'))
        elif self.model_type == 'both':
            domain.append(('res_model', 'in', ['crm.lead', 'project.project']))
        
        attachments = self.env['ir.attachment'].search(domain)
        
        if not attachments:
            raise UserError(_('لا توجد ملفات بدون تصنيف!'))
        
        attachments.write({
            'document_category_id': self.default_category_id.id
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('تم بنجاح!'),
                'message': _('تم ربط %s ملف بالتصنيف "%s"') % (
                    len(attachments),
                    self.default_category_id.name
                ),
                'type': 'success',
                'sticky': False,
            }
        }

