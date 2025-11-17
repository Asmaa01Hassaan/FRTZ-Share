# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ProjectProject(models.Model):
    _inherit = 'project.project'

    # إحصائيات الملفات حسب تصنيفات المشاريع
    achievement_files_count = fields.Integer(
        string='شهادات الإنجاز',
        compute='_compute_category_counts'
    )
    approval_docs_count = fields.Integer(
        string='توثيق موافقات',
        compute='_compute_category_counts'
    )
    technical_docs_count = fields.Integer(
        string='مستندات فنية',
        compute='_compute_category_counts'
    )
    project_reports_count = fields.Integer(
        string='تقارير المشروع',
        compute='_compute_category_counts'
    )
    project_contracts_count = fields.Integer(
        string='عقود المشروع',
        compute='_compute_category_counts'
    )
    invoices_payments_count = fields.Integer(
        string='فواتير ومستخلصات',
        compute='_compute_category_counts'
    )
    general_files_count = fields.Integer(
        string='ملفات عامة',
        compute='_compute_category_counts'
    )
    
    total_document_count = fields.Integer(
        string='إجمالي الملفات',
        compute='_compute_category_counts'
    )
    
    def _compute_category_counts(self):
        """حساب عدد الملفات لكل تصنيف مشاريع"""
        Attachment = self.env['ir.attachment']
        
        for project in self:
            domain_base = [
                ('res_model', '=', 'project.project'),
                ('res_id', '=', project.id)
            ]
            
            # العدد الكلي
            project.total_document_count = Attachment.search_count(domain_base)
            
            # حساب لكل تصنيف (التصنيفات الجديدة للمشاريع)
            categories = {
                'achievement_files_count': 'laft_document_management.category_project_achievement',
                'approval_docs_count': 'laft_document_management.category_project_approval',
                'technical_docs_count': 'laft_document_management.category_project_technical',
                'project_reports_count': 'laft_document_management.category_project_reports',
                'project_contracts_count': 'laft_document_management.category_project_contracts',
                'invoices_payments_count': 'laft_document_management.category_project_invoices',
                'general_files_count': 'laft_document_management.category_general',
            }
            
            for field_name, xml_id in categories.items():
                category = self.env.ref(xml_id, raise_if_not_found=False)
                if category:
                    # البحث عن الملفات بهذا التصنيف أو بدون تصنيف (للـ general)
                    if field_name == 'general_files_count':
                        # الملفات العامة = الملفات بتصنيف عام أو بدون تصنيف
                        count = Attachment.search_count(
                            domain_base + [
                                '|',
                                ('document_category_id', '=', category.id),
                                ('document_category_id', '=', False)
                            ]
                        )
                    else:
                        count = Attachment.search_count(
                            domain_base + [('document_category_id', '=', category.id)]
                        )
                    setattr(project, field_name, count)
                else:
                    setattr(project, field_name, 0)
    
    def action_view_documents(self, category_xml_id=None):
        """عرض الملفات (مع فلتر تصنيف اختياري)"""
        self.ensure_one()
        
        domain = [
            ('res_model', '=', 'project.project'),
            ('res_id', '=', self.id)
        ]
        
        if category_xml_id:
            category = self.env.ref(category_xml_id, raise_if_not_found=False)
            if category:
                domain.append(('document_category_id', '=', category.id))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('ملفات المشروع'),
            'res_model': 'ir.attachment',
            'view_mode': 'kanban,list,form',
            'domain': domain,
            'context': {
                'default_res_model': 'project.project',
                'default_res_id': self.id,
            }
        }
    
    # Actions لكل تصنيف
    def action_view_achievement_files(self):
        return self.action_view_documents('laft_document_management.category_project_achievement')
    
    def action_view_approval_docs(self):
        return self.action_view_documents('laft_document_management.category_project_approval')
    
    def action_view_technical_docs(self):
        return self.action_view_documents('laft_document_management.category_project_technical')
    
    def action_view_project_reports(self):
        return self.action_view_documents('laft_document_management.category_project_reports')
    
    def action_view_project_contracts(self):
        return self.action_view_documents('laft_document_management.category_project_contracts')
    
    def action_view_invoices_payments(self):
        return self.action_view_documents('laft_document_management.category_project_invoices')
    
    def action_view_general_files(self):
        return self.action_view_documents('laft_document_management.category_general')
    
    def action_quick_categorize_files(self):
        """فتح معالج لتصنيف الملفات بسرعة"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('تصنيف الملفات'),
            'res_model': 'quick.categorize.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
                'active_model': 'project.project',
            }
        }
    
    def action_view_all_documents(self):
        return self.action_view_documents()
    
    def action_upload_file(self):
        """فتح نافذة لرفع ملف جديد"""
        self.ensure_one()
        
        # تحديد التصنيف من الـ context
        category_map = {
            'achievement': 'laft_document_management.category_project_achievement',
            'approval': 'laft_document_management.category_project_approval',
            'technical': 'laft_document_management.category_project_technical',
            'reports': 'laft_document_management.category_project_reports',
            'contracts': 'laft_document_management.category_project_contracts',
            'invoices': 'laft_document_management.category_project_invoices',
            'general': 'laft_document_management.category_general',
        }
        
        category_key = self.env.context.get('default_category', 'general')
        category = self.env.ref(category_map.get(category_key, category_map['general']), raise_if_not_found=False)
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('إرفاق ملف'),
            'res_model': 'ir.attachment',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_res_model': 'project.project',
                'default_res_id': self.id,
                'default_document_category_id': category.id if category else False,
            }
        }
