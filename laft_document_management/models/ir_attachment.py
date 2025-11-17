# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    document_category_id = fields.Many2one(
        'document.category',
        string='التصنيف',
        index=True,
        help='تصنيف الملف حسب النوع'
    )
    
    # حقول محسوبة لسهولة الفلترة
    is_crm_document = fields.Boolean(
        string='ملف CRM',
        compute='_compute_document_type',
        store=True,
        index=True
    )
    is_project_document = fields.Boolean(
        string='ملف مشروع',
        compute='_compute_document_type',
        store=True,
        index=True
    )
    
    category_name = fields.Char(
        string='اسم التصنيف',
        related='document_category_id.name',
        readonly=True
    )
    
    category_icon = fields.Char(
        string='أيقونة التصنيف',
        related='document_category_id.icon'
    )
    
    category_color = fields.Integer(
        string='لون التصنيف',
        related='document_category_id.color'
    )
    
    @api.depends('res_model')
    def _compute_document_type(self):
        """تحديد نوع الملف (CRM أو Project)"""
        for record in self:
            record.is_crm_document = record.res_model == 'crm.lead'
            record.is_project_document = record.res_model == 'project.project'
    
    @api.model_create_multi
    def create(self, vals_list):
        """تعيين التصنيف الافتراضي عند الإنشاء"""
        general_category = self.env.ref(
            'laft_document_management.category_general',
            raise_if_not_found=False
        )
        
        for vals in vals_list:
            # إذا لم يتم تحديد تصنيف وكان الملف مرتبط بـ CRM أو Project، استخدم "ملفات عامة"
            if not vals.get('document_category_id') and general_category:
                res_model = vals.get('res_model')
                # فقط للملفات المرتبطة بـ CRM أو Projects
                if res_model in ['crm.lead', 'project.project']:
                    vals['document_category_id'] = general_category.id
        
        attachments = super().create(vals_list)
        
        # تحديث العدادات في CRM/Project مباشرة
        for attachment in attachments:
            if attachment.res_model == 'crm.lead' and attachment.res_id:
                lead = self.env['crm.lead'].browse(attachment.res_id)
                if lead.exists():
                    lead._compute_category_counts()
            elif attachment.res_model == 'project.project' and attachment.res_id:
                project = self.env['project.project'].browse(attachment.res_id)
                if project.exists():
                    project._compute_category_counts()
        
        return attachments
    
    def write(self, vals):
        """تحديث العدادات عند تغيير التصنيف"""
        res = super().write(vals)
        
        # إذا تم تغيير التصنيف، حدث العدادات
        if 'document_category_id' in vals:
            for attachment in self:
                if attachment.res_model == 'crm.lead' and attachment.res_id:
                    lead = self.env['crm.lead'].browse(attachment.res_id)
                    if lead.exists():
                        lead._compute_category_counts()
                elif attachment.res_model == 'project.project' and attachment.res_id:
                    project = self.env['project.project'].browse(attachment.res_id)
                    if project.exists():
                        project._compute_category_counts()
        
        return res
    
    def action_change_category(self):
        """فتح معالج لتغيير التصنيف"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('تغيير التصنيف'),
            'res_model': 'ir.attachment',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'form_view_ref': 'laft_document_management.view_attachment_category_form_dialog'
            }
        }
    
    def action_preview(self):
        """معاينة الملف"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.id}?download=false',
            'target': 'new',
        }
    
    def action_download(self):
        """تحميل الملف"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.id}?download=true',
            'target': 'self',
        }

