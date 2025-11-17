# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # إحصائيات الملفات حسب التصنيف
    opportunity_files_count = fields.Integer(
        string='ملفات الفرصة',
        compute='_compute_category_counts'
    )
    technical_files_count = fields.Integer(
        string='ملفات فنية',
        compute='_compute_category_counts'
    )
    financial_files_count = fields.Integer(
        string='ملفات مالية',
        compute='_compute_category_counts'
    )
    contract_files_count = fields.Integer(
        string='ملفات عقود',
        compute='_compute_category_counts'
    )
    purchase_files_count = fields.Integer(
        string='ملفات أوامر شراء',
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
        """حساب عدد الملفات لكل تصنيف CRM"""
        Attachment = self.env['ir.attachment']
        
        for lead in self:
            domain_base = [
                ('res_model', '=', 'crm.lead'),
                ('res_id', '=', lead.id)
            ]
            
            # العدد الكلي
            lead.total_document_count = Attachment.search_count(domain_base)
            
            # حساب لكل تصنيف (التصنيفات الجديدة)
            categories = {
                'opportunity_files_count': 'laft_document_management.category_opportunity',  # crm_opportunity
                'technical_files_count': 'laft_document_management.category_technical',     # crm_technical
                'financial_files_count': 'laft_document_management.category_financial',     # crm_financial
                'contract_files_count': 'laft_document_management.category_contract',       # crm_contract
                'purchase_files_count': 'laft_document_management.category_purchase',       # crm_purchase
                'general_files_count': 'laft_document_management.category_general',         # general_files
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
                    setattr(lead, field_name, count)
                else:
                    setattr(lead, field_name, 0)
    
    def action_view_documents(self, category_xml_id=None):
        """عرض الملفات (مع فلتر تصنيف اختياري)"""
        self.ensure_one()
        
        domain = [
            ('res_model', '=', 'crm.lead'),
            ('res_id', '=', self.id)
        ]
        
        if category_xml_id:
            category = self.env.ref(category_xml_id, raise_if_not_found=False)
            if category:
                domain.append(('document_category_id', '=', category.id))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('ملفات الفرصة'),
            'res_model': 'ir.attachment',
            'view_mode': 'kanban,list,form',
            'domain': domain,
            'context': {
                'default_res_model': 'crm.lead',
                'default_res_id': self.id,
            }
        }
    
    # Actions لكل تصنيف
    def action_view_opportunity_files(self):
        return self.action_view_documents('laft_document_management.category_opportunity')
    
    def action_view_technical_files(self):
        return self.action_view_documents('laft_document_management.category_technical')
    
    def action_view_financial_files(self):
        return self.action_view_documents('laft_document_management.category_financial')
    
    def action_view_contract_files(self):
        return self.action_view_documents('laft_document_management.category_contract')
    
    def action_view_purchase_files(self):
        return self.action_view_documents('laft_document_management.category_purchase')
    
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
                'active_model': 'crm.lead',
            }
        }
    
    def action_view_all_documents(self):
        return self.action_view_documents()
    
    def action_upload_file(self):
        """فتح نافذة لرفع ملف جديد"""
        self.ensure_one()
        
        # تحديد التصنيف من الـ context
        category_map = {
            'opportunity': 'laft_document_management.category_opportunity',
            'technical': 'laft_document_management.category_technical',
            'financial': 'laft_document_management.category_financial',
            'contract': 'laft_document_management.category_contract',
            'purchase': 'laft_document_management.category_purchase',
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
                'default_res_model': 'crm.lead',
                'default_res_id': self.id,
                'default_document_category_id': category.id if category else False,
            }
        }

