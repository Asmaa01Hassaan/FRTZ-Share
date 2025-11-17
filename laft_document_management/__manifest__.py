# -*- coding: utf-8 -*-
{
    'name': 'LAFT Document Management',
    'version': '18.0.1.0.0',
    'category': 'Productivity',
    'summary': 'نظام متقدم لإدارة وتصنيف الملفات في CRM والمشاريع',
    'description': """
        LAFT Document Management System
        ================================
        
        نظام شامل لإدارة الملفات مع التصنيفات:
        
        الميزات الرئيسية:
        ----------------
        * تصنيف الملفات إلى 6 فئات رئيسية
        * تاب خاص للملفات في الفرص (CRM)
        * تاب خاص للملفات في المشاريع
        * مركز ملفات مركزي مع لوحة تحكم حديثة
        * واجهة مستخدم عصرية وسهلة الاستخدام
        * إمكانية تغيير التصنيف ومعاينة الملفات
        * فلاتر متقدمة وبحث ذكي
        
        التصنيفات:
        ----------
        1. ملفات الفرصة
        2. ملفات فنية
        3. ملفات مالية
        4. ملفات عقود
        5. ملفات أوامر شراء
        6. ملفات عامة (افتراضي)
    """,
    'author': 'LAFT Company',
    'website': 'https://www.laft.com.sa',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'crm',
        'project',
        'mail',
        'web',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        
        # Data
        'data/document_categories.xml',
        
        # Wizards
        'wizard/categorize_attachments_wizard_views.xml',
        'wizard/quick_categorize_wizard_views.xml',
        
        # Views
        'views/document_category_views.xml',
        'views/ir_attachment_views.xml',
        'views/crm_lead_views.xml',
        'views/project_project_views.xml',
        'views/document_center_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'laft_document_management/static/src/css/document_manager.css',
            'laft_document_management/static/src/js/document_manager.js',
            'laft_document_management/static/src/xml/document_templates.xml',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}

