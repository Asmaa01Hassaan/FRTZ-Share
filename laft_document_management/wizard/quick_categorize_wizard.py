# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class QuickCategorizeWizard(models.TransientModel):
    _name = 'quick.categorize.wizard'
    _description = 'تصنيف سريع للملفات'

    lead_id = fields.Many2one('crm.lead', string='الفرصة')
    project_id = fields.Many2one('project.project', string='المشروع')
    record_type = fields.Selection([
        ('crm', 'فرصة CRM'),
        ('project', 'مشروع'),
    ], string='نوع السجل', compute='_compute_record_type')
    line_ids = fields.One2many(
        'quick.categorize.wizard.line',
        'wizard_id',
        string='الملفات'
    )
    attachment_count = fields.Integer(
        string='عدد الملفات',
        compute='_compute_attachment_count'
    )
    
    @api.depends('lead_id', 'project_id')
    def _compute_record_type(self):
        for wizard in self:
            if wizard.lead_id:
                wizard.record_type = 'crm'
            elif wizard.project_id:
                wizard.record_type = 'project'
            else:
                wizard.record_type = False
    
    @api.depends('line_ids')
    def _compute_attachment_count(self):
        for wizard in self:
            wizard.attachment_count = len(wizard.line_ids)
    
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        
        if not active_id or not active_model:
            return res
        
        # تحديد نوع السجل
        if active_model == 'crm.lead':
            res['lead_id'] = active_id
            res_model = 'crm.lead'
        elif active_model == 'project.project':
            res['project_id'] = active_id
            res_model = 'project.project'
        else:
            return res
        
        # البحث عن الملفات بدون تصنيف أو بتصنيف "عام"
        general_category = self.env.ref(
            'laft_document_management.category_general',
            raise_if_not_found=False
        )
        
        domain = [
            ('res_model', '=', res_model),
            ('res_id', '=', active_id),
            '|',
            ('document_category_id', '=', False),
            ('document_category_id', '=', general_category.id if general_category else False)
        ]
        
        attachments = self.env['ir.attachment'].search(domain)
        
        # إنشاء lines
        lines = []
        for att in attachments:
            lines.append((0, 0, {
                'attachment_id': att.id,
                'current_category_id': att.document_category_id.id if att.document_category_id else False,
                'new_category_id': general_category.id if general_category else False,
            }))
        
        res['line_ids'] = lines
        
        return res
    
    def action_apply_categories(self):
        """تطبيق التصنيفات الجديدة"""
        self.ensure_one()
        
        for line in self.line_ids:
            if line.new_category_id:
                line.attachment_id.write({
                    'document_category_id': line.new_category_id.id
                })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('تم بنجاح!'),
                'message': _('تم تحديث تصنيف %s ملف') % len(self.line_ids),
                'type': 'success',
                'sticky': False,
            }
        }


class QuickCategorizeWizardLine(models.TransientModel):
    _name = 'quick.categorize.wizard.line'
    _description = 'سطر تصنيف الملف'

    wizard_id = fields.Many2one('quick.categorize.wizard', string='المعالج', required=True, ondelete='cascade')
    attachment_id = fields.Many2one('ir.attachment', string='الملف', required=True)
    attachment_name = fields.Char(related='attachment_id.name', string='اسم الملف', readonly=True)
    current_category_id = fields.Many2one('document.category', string='التصنيف الحالي', readonly=True)
    record_type = fields.Selection(related='wizard_id.record_type', string='نوع السجل', store=False)
    new_category_id = fields.Many2one(
        'document.category', 
        string='التصنيف الجديد', 
        required=True
    )
    
    @api.onchange('wizard_id')
    def _onchange_wizard_id(self):
        """تحديث domain للتصنيفات حسب نوع السجل"""
        domain = []
        if self.wizard_id:
            if self.wizard_id.record_type == 'crm':
                domain = [('category_type', 'in', ['crm', 'general'])]
            elif self.wizard_id.record_type == 'project':
                domain = [('category_type', 'in', ['project', 'general'])]
        return {'domain': {'new_category_id': domain}}
