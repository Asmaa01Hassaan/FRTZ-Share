# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class DocumentCategory(models.Model):
    _name = 'document.category'
    _description = 'Document Category'
    _order = 'sequence, name'

    name = fields.Char(
        string='اسم التصنيف',
        required=True,
        translate=True
    )
    code = fields.Char(
        string='الرمز',
        required=True,
        help='رمز فريد للتصنيف (مثال: technical_files)'
    )
    sequence = fields.Integer(
        string='الترتيب',
        default=10,
        help='يحدد ترتيب ظهور التصنيف'
    )
    color = fields.Integer(
        string='اللون',
        default=0,
        help='اللون المستخدم في الواجهة'
    )
    icon = fields.Char(
        string='الأيقونة',
        default='fa-file-o',
        help='Font Awesome icon class (مثال: fa-folder)'
    )
    active = fields.Boolean(
        string='نشط',
        default=True
    )
    description = fields.Text(
        string='الوصف',
        translate=True
    )
    
    category_type = fields.Selection([
        ('crm', 'تطوير الأعمال (CRM)'),
        ('project', 'المشاريع'),
        ('general', 'عام - مشترك'),
    ], string='نوع التصنيف', default='general', required=True)
    
    is_system = fields.Boolean(
        string='تصنيف نظام',
        default=False,
        help='التصنيفات النظامية لا يمكن حذفها (مثل: ملفات عامة)'
    )
    
    # Statistics
    attachment_count = fields.Integer(
        string='عدد الملفات',
        compute='_compute_attachment_count',
        store=True
    )
    
    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'رمز التصنيف يجب أن يكون فريداً!')
    ]
    
    @api.depends('code')
    def _compute_attachment_count(self):
        """حساب عدد الملفات لكل تصنيف"""
        for category in self:
            category.attachment_count = self.env['ir.attachment'].search_count([
                ('document_category_id', '=', category.id)
            ])
    
    def unlink(self):
        """منع حذف التصنيفات النظامية"""
        for category in self:
            if category.is_system:
                raise UserError(_(
                    'لا يمكن حذف التصنيف "%s" لأنه تصنيف نظام.'
                ) % category.name)
        return super().unlink()
    
    def action_view_attachments(self):
        """عرض جميع الملفات في هذا التصنيف"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'ملفات: {self.name}',
            'res_model': 'ir.attachment',
            'view_mode': 'kanban,list,form',
            'domain': [('document_category_id', '=', self.id)],
            'context': {
                'default_document_category_id': self.id,
                'search_default_group_by_res_model': 1,
            }
        }

