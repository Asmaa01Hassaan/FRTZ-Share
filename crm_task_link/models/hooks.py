from odoo import models, fields, api, _
from datetime import datetime
import calendar
import json

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    project_id = fields.Many2one('project.project')

class OperationalExpenseCategory(models.Model):
    _name = 'operational.expense.category'
    _description = 'فئات المصاريف التشغيلية'

    name = fields.Char(string='اسم الفئة', required=True)


class OperationalExpense(models.Model):
    _name = 'operational.expense'
    _description = 'المصاريف التشغيلية'

    category_id = fields.Many2one('operational.expense.category', string='الفئة', required=True)
    description = fields.Text(string='الوصف')
    date = fields.Date(string='التاريخ', default=fields.Date.today)
    amount = fields.Float(string='المبلغ', required=True)
    lead_id = fields.Many2one('crm.lead', string='فرصة مرتبطة')
    allocated_hours = fields.Float(string='الساعات المخصصة')

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    opportunity_id = fields.Many2one('crm.lead', string="Opportunity")

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    project_id = fields.Many2one('project.project', string="Related Project")
    expense_ids = fields.One2many('hr.expense', 'lead_id', string="Expenses")
    
    default_expense_analytic_distribution = fields.Json(
        string="Default Expense Analytic Distribution",
        compute="_compute_default_expense_analytic_distribution",
        store=False,
    )

    def _compute_default_expense_analytic_distribution(self):
        """Compute default analytic distribution for expenses from project."""
        for lead in self:
            if lead.project_id:
                lead.default_expense_analytic_distribution = lead.project_id._ensure_default_analytic_distribution() or {}
            else:
                lead.default_expense_analytic_distribution = {}
    operational_expense_ids = fields.One2many(
        'operational.expense',
        'lead_id',
        string='المصاريف التشغيلية'
    )


    operational_expense_total = fields.Monetary(
        string="إجمالي المصاريف",
        compute='_compute_operational_expense_total',
        currency_field='company_currency'
    )

    @api.depends('operational_expense_ids.amount')
    def _compute_operational_expense_total(self):
        for rec in self:
            rec.operational_expense_total = sum(rec.operational_expense_ids.mapped('amount'))

    total_expense_amount = fields.Monetary(
        string='إجمالي المصاريف',
        compute='_compute_total_expense_amount',
        currency_field='company_currency',
        store=True
    )
    company_currency = fields.Many2one(
        related='company_id.currency_id', readonly=True
    )

    @api.depends('expense_ids.total_amount')
    def _compute_total_expense_amount(self):
        for rec in self:
            rec.total_expense_amount = sum(line.total_amount for line in rec.expense_ids)

    # def action_open_expense_lines(self):
    #     self.ensure_one()
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Expenses',
    #         'view_mode': 'tree,form',
    #         'res_model': 'hr.expense',
    #         'domain': [('lead_id', '=', self.id)],
    #         'context': {
    #             'default_lead_id': self.id,
    #             'search_default_lead_id': self.id,
    #         },
    #     }

    quotation_ids = fields.One2many(
        'sale.order', 'opportunity_id', string='Quotations'
    )
    #
    total_quotation_untaxed = fields.Monetary(
        string="إجمالي السعر بدون ضريبة",
        compute="_compute_quotation_totals",
        currency_field="company_currency"
    )
    total_quotation_tax = fields.Monetary(
        string="إجمالي الضريبة",
        compute="_compute_quotation_totals",
        currency_field="company_currency"
    )
    total_quotation_total = fields.Monetary(
        string="الإجمالي الكلي",
        compute="_compute_quotation_totals",
        currency_field="company_currency"
    )
    total_revenue_amount = fields.Monetary(
        string="الإجمالي الكلي",
        compute="_compute_total_revenue_amount",
        currency_field="company_currency"
    )

    company_currency = fields.Many2one(
        related="company_id.currency_id",
        readonly=True,
        string="العملة"
    )
    revenue_margin_percent = fields.Float(
        string="هامش الربح (%)",
        compute="_compute_total_revenue_amount",
        store=True
    )
    #
    @api.depends('quotation_ids.amount_total', 'quotation_ids.amount_tax', 'quotation_ids.amount_untaxed')
    def _compute_quotation_totals(self):
        for lead in self:
            lead.total_quotation_untaxed = sum(lead.quotation_ids.mapped('amount_untaxed'))
            lead.total_quotation_tax = sum(lead.quotation_ids.mapped('amount_tax'))
            lead.total_quotation_total = sum(lead.quotation_ids.mapped('amount_total'))

    @api.depends('expense_ids.total_amount','quotation_ids.amount_untaxed')
    def _compute_total_revenue_amount(self):
        for rec in self:
            rec.total_revenue_amount = rec.total_quotation_total - rec.total_expense_amount
            if rec.total_quotation_total:
                rec.revenue_margin_percent = (rec.total_revenue_amount / rec.total_quotation_total) * 100

    revenue_margin_color = fields.Selection(
        selection=[
            ('success', 'High'),
            ('warning', 'Medium'),
            ('danger', 'Low'),
        ],
        compute='_compute_margin_color'
    )


    @api.depends('revenue_margin_percent')
    def _compute_margin_color(self):
        for rec in self:
            if rec.revenue_margin_percent >= 50:
                rec.revenue_margin_color = 'success'
            elif rec.revenue_margin_percent >= 25:
                rec.revenue_margin_color = 'warning'
            else:
                rec.revenue_margin_color = 'danger'

    revenue_css_class = fields.Char(
        compute="_compute_revenue_css_class"
    )

    @api.depends('revenue_margin_percent')
    def _compute_revenue_css_class(self):
        for rec in self:
            if rec.revenue_margin_percent >= 50:
                rec.revenue_css_class = 'bg-success text-white'
            elif rec.revenue_margin_percent >= 25:
                rec.revenue_css_class = 'bg-warning text-dark'
            else:
                rec.revenue_css_class = 'bg-danger text-white'
    
    # ===== إحصائيات ذكية للفرصة =====
    opportunity_age_days = fields.Integer(
        string="عمر الفرصة (أيام)",
        compute="_compute_opportunity_statistics"
    )
    
    days_until_deadline = fields.Integer(
        string="الأيام المتبقية",
        compute="_compute_opportunity_statistics"
    )
    
    is_deadline_overdue = fields.Boolean(
        string="متأخرة عن الموعد",
        compute="_compute_opportunity_statistics"
    )
    
    has_files = fields.Boolean(
        string="يوجد ملفات",
        compute="_compute_opportunity_statistics"
    )
    
    files_status_message = fields.Char(
        string="رسالة حالة الملفات",
        compute="_compute_opportunity_statistics"
    )
    
    files_status_color = fields.Char(
        string="لون حالة الملفات",
        compute="_compute_opportunity_statistics"
    )
    
    opportunity_status_color = fields.Char(
        string="لون حالة الفرصة",
        compute="_compute_opportunity_statistics"
    )
    
    has_opportunity_warning = fields.Boolean(
        string="تحذيرات",
        compute="_compute_opportunity_statistics"
    )
    
    warning_count = fields.Integer(
        string="عدد التحذيرات",
        compute="_compute_opportunity_statistics"
    )
    
    warning_messages = fields.Text(
        string="رسائل التحذيرات",
        compute="_compute_opportunity_statistics"
    )
    
    @api.depends('create_date', 'date_deadline', 'contract_files_count', 'purchase_files_count', 
                 'stage_id', 'project_id', 'revenue_margin_percent', 'total_quotation_total')
    def _compute_opportunity_statistics(self):
        """حساب الإحصائيات الذكية للفرصة"""
        from datetime import date
        
        for lead in self:
            today = date.today()
            
            # 1. عمر الفرصة
            if lead.create_date:
                create_date = lead.create_date.date()
                lead.opportunity_age_days = (today - create_date).days
            else:
                lead.opportunity_age_days = 0
            
            # 2. الأيام المتبقية حتى الموعد النهائي
            if lead.date_deadline:
                lead.days_until_deadline = (lead.date_deadline - today).days
                lead.is_deadline_overdue = lead.days_until_deadline < 0
            else:
                lead.days_until_deadline = 0
                lead.is_deadline_overdue = False
            
            # 3. حالة الملفات (عقود + أوامر شراء)
            contract_count = lead.contract_files_count if hasattr(lead, 'contract_files_count') else 0
            po_count = lead.purchase_files_count if hasattr(lead, 'purchase_files_count') else 0
            
            if contract_count > 0 or po_count > 0:
                lead.has_files = True
                lead.files_status_color = 'success'
                lead.files_status_message = f"✓ {contract_count} عقد، {po_count} أمر شراء"
            else:
                lead.has_files = False
                lead.files_status_color = 'warning'
                lead.files_status_message = "⚠ لا توجد ملفات"
            
            # 4. لون حالة الفرصة (بناءً على stage)
            if lead.stage_id:
                stage_name = lead.stage_id.name
                if 'Won' in stage_name or 'الترسية' in stage_name:
                    lead.opportunity_status_color = 'success'
                elif 'Lost' in stage_name or 'لم تتم' in stage_name:
                    lead.opportunity_status_color = 'danger'
                else:
                    lead.opportunity_status_color = 'info'
            else:
                lead.opportunity_status_color = 'secondary'
            
            # 5. التحذيرات الذكية (Smart Warnings)
            warnings_red = []    # 🔴 Critical
            warnings_yellow = [] # 🟡 Warning
            
            stage_name = lead.stage_id.name if lead.stage_id else ''
            
            # الحالات المستثناة من فحص هامش الربح
            exempted_stages = [
                'فرصة جديدة',
                'مراجعة الفرصة',
                'التواصل مع العميل',
                'دعم الأقسام الأخرى',

            ]
            
            # === تحذيرات حمراء (Critical) ===
            
            # 1. فرصة متأخرة عن الموعد
            if lead.is_deadline_overdue:
                warnings_red.append("🔴 متأخرة عن الموعد")
            
            # 2. Won + لا يوجد عقد/أمر شراء
            if ('Won' in stage_name or 'الترسية' in stage_name):
                if contract_count == 0 and po_count == 0:
                    warnings_red.append("🔴 لا يوجد عقد او امر شراء يجب النظر عاجلاً")
            
            # 3. Won + لا يوجد هامش ربح (لم يتم إكمال الحاسبة)
            if ('Won' in stage_name or 'الترسية' in stage_name):
                if lead.total_quotation_total == 0 or lead.revenue_margin_percent == 0:
                    warnings_red.append("🔴 يجب اكمال حاسبة المشروع")
            
            # 4. هامش الربح < 15% (في الحالات غير المستثناة)
            if stage_name not in exempted_stages:
                if lead.total_quotation_total > 0 and lead.revenue_margin_percent < 15:
                    warnings_red.append("🔴 هامش الربح اقل من المعتمد")
            
            # === تحذيرات صفراء (Warning) ===
            
            # 1. تنتهي خلال أسبوع
            if lead.days_until_deadline > 0 and lead.days_until_deadline <= 7:
                warnings_yellow.append("🟡 تنتهي خلال أسبوع")
            
            # 2. لا يوجد مشروع مرتبط
            if not lead.project_id:
                warnings_yellow.append("🟡 برجاء ربط الفرصة بالمشروع الخاص بها إن وجد")
            
            # 3. تم التقديم + لا يوجد هامش ربح
            if 'تم التقديم' in stage_name:
                if lead.total_quotation_total == 0 or lead.revenue_margin_percent == 0:
                    warnings_yellow.append("🟡 يجب اكمال حاسبة المشروع")
            
            # 4. هامش الربح بين 15% و 20% (في الحالات غير المستثناة)
            if stage_name not in exempted_stages:
                if lead.total_quotation_total > 0 and 15 <= lead.revenue_margin_percent < 20:
                    warnings_yellow.append("🟡 هامش الربح اقل من المعتمد")
            
            # حساب العدد والرسائل
            all_warnings = warnings_red + warnings_yellow
            lead.warning_count = len(all_warnings)
            lead.has_opportunity_warning = lead.warning_count > 0
            lead.warning_messages = '\n'.join(all_warnings) if all_warnings else ''
class DocumentLine(models.Model):
    _name = 'laft.document.line'
    _description = 'Document Line'

    name = fields.Char()
    description = fields.Char()
    attachment_ids = fields.Many2many('ir.attachment', string="Documents")
    passed = fields.Selection(selection=[('yes', 'مقبول'), ('no', 'مرفوض')], default='no',help="the manger should if selected")
    required = fields.Boolean(string='Required',help="it will be send to the manger if selected")
    user_id = fields.Many2one('res.users', string='Project Manager', readonly=True , store=True)
    project_id = fields.Many2one('project.project', string="Related Project")

    @api.onchange('passed')
    def _onchange_passed(self):
        if self.passed == 'yes':
            self.user_id = self.env.user

    @api.model
    def create(self, vals):
        if vals.get('passed') == 'yes' and not vals.get('user_id'):
            vals['user_id'] = self.env.uid
        return super().create(vals)

    def write(self, vals):
        if vals.get('passed') == 'yes' and not vals.get('user_id'):
            vals['user_id'] = self.env.uid
        return super().write(vals)

class HrExpense(models.Model):
    _inherit = 'hr.expense'
    lead_id = fields.Many2one('crm.lead', string="Opportunity")
    project_id = fields.Many2one('project.project', string="Project", compute="_compute_project", store=True)
    currency_id = fields.Many2one('res.currency', string='Currency')

    # Any custom monetary fields you add MUST reference it
    # custom_amount = fields.Monetary(string="Custom Amount", currency_field='currency_id')

    @api.depends('lead_id', 'project_id', 'analytic_distribution')
    def _compute_project(self):
        """Compute project_id from lead_id."""
        for expense in self:
            # If we have lead_id, get project from it
            if expense.lead_id and expense.lead_id.project_id:
                expense.project_id = expense.lead_id.project_id

    @api.model
    def default_get(self, fields_list):
        """Set default analytic_distribution from project if available."""
        res = super().default_get(fields_list)
        if 'analytic_distribution' in fields_list and not res.get('analytic_distribution'):
            project = None
            project_id = None
            
            # Case 1: Creating from CRM Lead (via lead_id context)
            if self._context.get('default_lead_id'):
                lead = self.env['crm.lead'].browse(self._context.get('default_lead_id'))
                if lead.exists() and lead.project_id:
                    project = lead.project_id
                    project_id = project.id
                    # Also set lead_id if not already set
                    if 'lead_id' in fields_list and not res.get('lead_id'):
                        res['lead_id'] = lead.id
            
            # Case 2: Creating from Project (via project_id context)
            if not project:
                project_id = (
                    self._context.get('default_project_id') or 
                    self._context.get('active_id')
                )
                if project_id and (
                    self._context.get('active_model') == 'project.project' or
                    self._context.get('default_project_id')
                ):
                    project = self.env['project.project'].browse(project_id)
            
            # Set analytic_distribution from project
            if project and project.exists():
                analytic_distribution = project._ensure_default_analytic_distribution()
                if analytic_distribution:
                    res['analytic_distribution'] = analytic_distribution
                # Also set project_id if not already set
                if 'project_id' in fields_list and not res.get('project_id'):
                    res['project_id'] = project_id
        return res

    @api.model
    def create(self, vals):
        # Set project_id from context if not set
        if not vals.get('project_id') and self._context.get('default_project_id'):
            vals['project_id'] = self._context.get('default_project_id')
        
        # Set lead_id from context if not set
        if not vals.get('lead_id') and self._context.get('default_lead_id'):
            vals['lead_id'] = self._context.get('default_lead_id')
        
        # If project_id is set but lead_id is not, try to find lead from project
        if vals.get('project_id') and not vals.get('lead_id'):
            project = self.env['project.project'].browse(vals['project_id'])
            if project.exists() and project.crm_lead_ids:
                # Link to the first CRM lead associated with the project
                vals['lead_id'] = project.crm_lead_ids[0].id
        
        # Set analytic_distribution from project if not set
        if not vals.get('analytic_distribution') and vals.get('project_id'):
            project = self.env['project.project'].browse(vals['project_id'])
            if project.exists():
                analytic_distribution = project._ensure_default_analytic_distribution()
                if analytic_distribution:
                    vals['analytic_distribution'] = analytic_distribution
        
        # If we have lead_id but no project_id, get it from lead
        if vals.get('lead_id') and not vals.get('project_id'):
            lead = self.env['crm.lead'].browse(vals['lead_id'])
            if lead.exists() and lead.project_id:
                vals['project_id'] = lead.project_id.id
                # Also set analytic_distribution if not set
                if not vals.get('analytic_distribution'):
                    analytic_distribution = lead.project_id._ensure_default_analytic_distribution()
                    if analytic_distribution:
                        vals['analytic_distribution'] = analytic_distribution
        
        return super().create(vals)
    
    def write(self, vals):
        """Keep lead_id and project_id in sync, and update analytic_distribution from project."""
        # If project_id is being set but lead_id is not, try to find lead from project
        if 'project_id' in vals and not vals.get('lead_id'):
            project = self.env['project.project'].browse(vals['project_id'])
            if project.exists() and project.crm_lead_ids:
                vals['lead_id'] = project.crm_lead_ids[0].id
        
        # If lead_id is being set but project_id is not, get project from lead
        if 'lead_id' in vals and not vals.get('project_id'):
            lead = self.env['crm.lead'].browse(vals['lead_id'])
            if lead.exists() and lead.project_id:
                vals['project_id'] = lead.project_id.id
        
        # If project_id is being set/changed, update analytic_distribution if not explicitly set
        if 'project_id' in vals and 'analytic_distribution' not in vals:
            project = self.env['project.project'].browse(vals['project_id'])
            if project.exists():
                analytic_distribution = project._ensure_default_analytic_distribution()
                if analytic_distribution:
                    vals['analytic_distribution'] = analytic_distribution
        
        return super().write(vals)


class AccountMove(models.Model):
    _inherit = 'account.move'

    project_id = fields.Many2one('project.project', string="Project")


class ProjectProject(models.Model):
    _inherit = 'project.project'

    def _ensure_default_analytic_distribution(self):
        """Ensure each analytic plan column has an account and return a full distribution."""
        self.ensure_one()
        plan_model = self.env['account.analytic.plan']
        project_plan, other_plans = plan_model._get_all_plans()
        plans = project_plan + other_plans

        for plan in plans:
            field_name = plan._column_name()
            if field_name not in self._fields:
                continue

            if not self[field_name]:
                account_vals = {
                    'name': f"{self.name or _('Project')} - {plan.name}",
                    'company_id': self.company_id.id if self.company_id else False,
                    'partner_id': self.partner_id.id if getattr(self, 'partner_id', False) else False,
                    'plan_id': plan.id,
                }
                account = self.env['account.analytic.account'].create(account_vals)
                self[field_name] = account.id

        return self._get_analytic_distribution()

    default_expense_analytic_distribution = fields.Json(
        string="Default Expense Analytic Distribution",
        compute="_compute_default_expense_analytic_distribution",
        store=False,
    )

    def _compute_default_expense_analytic_distribution(self):
        """Compute default analytic distribution for expenses."""
        for project in self:
            project.default_expense_analytic_distribution = project._ensure_default_analytic_distribution() or {}

    user_id = fields.Many2one('res.users', string='Project Manager')
    exporter_document_line_ids = fields.One2many('laft.document.line', 'project_id')
    expense_ids = fields.One2many('hr.expense', 'project_id', string="Expenses")
    allocated_hours = fields.Float(string="Allocated Hours")
    allow_timesheets = fields.Boolean(string="Allow Timesheets", default=True)
    date_end = fields.Date(string="Planned End Date")
    task_ids = fields.One2many('project.task', 'project_id', string="Tasks")
    crm_lead_ids = fields.One2many('crm.lead', 'project_id', string='CRM Leads')
    timeline_html = fields.Html(string="Timeline", compute="_compute_timeline_html", sanitize=False)
    company_currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', readonly=True
    )
    
    # ===== حقول الإحصائيات الذكية للمشروع =====
    project_age_days = fields.Integer(
        string="عمر المشروع (أيام)",
        compute="_compute_project_statistics"
    )
    has_contract = fields.Boolean(
        string="هل يوجد عقد؟",
        compute="_compute_project_statistics"
    )
    has_warning = fields.Boolean(
        string="تحذيرات",
        compute="_compute_project_statistics"
    )
    project_status_message = fields.Char(
        string="رسالة الحالة",
        compute="_compute_project_statistics"
    )
    contract_status_color = fields.Char(
        string="لون حالة العقد",
        compute="_compute_project_statistics"
    )
    days_remaining = fields.Integer(
        string="الأيام المتبقية",
        compute="_compute_project_statistics"
    )
    is_overdue = fields.Boolean(
        string="متأخر عن الموعد",
        compute="_compute_project_statistics"
    )



    operational_expense_ids = fields.One2many(
            comodel_name='operational.expense',
            inverse_name='lead_id',
            string='Operational Expenses',
            related='crm_lead_ids.operational_expense_ids',
            readonly=False
        )
    operational_expense_total = fields.Monetary(
        string="إجمالي المصاريف",
        compute='_compute_operational_expense_ids',
        related='crm_lead_ids.operational_expense_total',
        readonly=True
    )
    purchase_order_count = fields.Integer(
        string="Purchase Orders",
        compute="_compute_purchase_order_count",
    )

    vendor_bill_count = fields.Integer(string="فواتير الموردين", compute='_compute_vendor_bill_count',store=True)

    def _compute_vendor_bill_count(self):
        for project in self:
            project.vendor_bill_count = self.env['account.move'].search_count([
                ('move_type', '=', 'in_invoice'),
                ('project_id', '=', project.id)
            ])


    def action_view_vendor_bills(self):
        self.ensure_one()
        analytic_distribution = self._ensure_default_analytic_distribution()

        bills = self.env['account.move'].search([
            ('move_type', '=', 'in_invoice'),
            ('project_id', '=', self.id)
        ])
        ctx = {
            'default_project_id': self.id,
            'default_move_type': 'in_invoice',
            'default_invoice_line_ids': [
                (0, 0, {
                    "analytic_distribution": analytic_distribution or {},
                })
            ],
        }

        action = {
            'name': 'Vendor Bills',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'type': 'ir.actions.act_window',
            'context': ctx,
            'domain': [
                ('move_type', '=', 'in_invoice'),
                ('project_id', '=', self.id),
            ],
        }
        return action


    project_expense_total = fields.Monetary(
        string="Total Expenses",
        compute="_compute_project_expense_total",
        currency_field='company_currency'
    )
    company_currency = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        string="Currency",
        readonly=True
    )

    def _compute_purchase_order_count(self):
        PO = self.env['purchase.order']
        po_has_project = 'project_id' in PO._fields
        proj_has_aa = 'analytic_account_id' in self._fields  # <- defensive check

        for project in self:
            domain = []
            if proj_has_aa and project.analytic_account_id:
                # Link via PO lines' analytic account (classic approach)
                domain = [('order_line.account_analytic_id', '=', project.analytic_account_id.id)]
            elif po_has_project:
                # Fallback: direct link if your PO has project_id (customization)
                domain = [('project_id', '=', project.id)]
            else:
                project.purchase_order_count = 0
                continue

            project.purchase_order_count = PO.search_count(domain)

    def action_view_purchase_orders(self):
        self.ensure_one()

        PO = self.env['purchase.order']
        po_has_project = 'project_id' in PO._fields
        proj_has_aa = 'analytic_account_id' in self._fields

        # Domain: filter POs related to this project or analytic account
        domain = []
        if proj_has_aa and self.analytic_account_id:
            domain = [('order_line.account_analytic_id', '=', self.analytic_account_id.id)]
        elif po_has_project:
            domain = [('project_id', '=', self.id)]

        # Prepare action from the original Purchase RFQ action
        action = self.env["ir.actions.actions"]._for_xml_id("purchase.purchase_rfq")

        # Force list view first, then form view
        try:
            list_view = self.env.ref("purchase.purchase_order_view_tree").id
            form_view = self.env.ref("purchase.purchase_order_form").id
            action["views"] = [(list_view, "list"), (form_view, "form")]
        except Exception:
            pass

        # Update domain
        action["domain"] = domain

        # Update context defaults
        ctx = dict(self.env.context or {})
        ctx.update({
            "default_project_id": self.id if po_has_project else False,
            "default_origin": self.name,
        })
        action["context"] = ctx

        return action

    def action_view_customer_invoices(self):
        self.ensure_one()

        # Prepare analytic distribution for new invoice creation
        analytic = self._ensure_default_analytic_distribution()

        ctx = {
            'default_project_id': self.id,
            'default_move_type': 'out_invoice',
            'default_invoice_line_ids': [
                (0, 0, {
                    'analytic_distribution': analytic,
                })
            ],
        }

        return {
            'name': 'Customer Invoices',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [
                ('move_type', '=', 'out_invoice'),
                ('project_id', '=', self.id),
            ],
            'context': ctx,
        }



    def action_view_expense(self):
        self.ensure_one()

        # Get original HR Expense action
        action = self.env["ir.actions.actions"]._for_xml_id(
            "hr_expense.hr_expense_actions_my_all"
        )
        analytic_distribution = self._ensure_default_analytic_distribution()

        # Force list then form view
        try:
            list_view = self.env.ref("hr_expense.hr_expense_view_tree").id
            form_view = self.env.ref("hr_expense.hr_expense_view_form").id
            action["views"] = [(list_view, "list"), (form_view, "form")]
        except Exception:
            pass

        # Show only expenses for this project
        action["domain"] = [
            ("project_id", "=", self.id),
        ]

        # Default context when creating new expense
        ctx = dict(self.env.context or {})
        ctx.update({
            "default_project_id": self.id,
            "default_analytic_distribution": analytic_distribution or {},
        })
        action["context"] = ctx

        return action


    def _compute_project_expense_total(self):
        for rec in self:
            expenses = self.env['hr.expense'].search([('project_id', '=', rec.id)])
            rec.project_expense_total = sum(exp.total_amount for exp in expenses)

    @api.depends('crm_lead_ids.operational_expense_ids')
    def _compute_operational_expense_ids(self):
        for project in self:
            lead = project.crm_lead_ids[:1]
            if lead:
                project.operational_expense_ids = lead.operational_expense_ids if lead else []
                project.operational_expense_total = lead.operational_expense_total if lead else 0.0

    @api.depends('task_ids.date_deadline', 'task_ids.name')
    def _compute_timeline_html(self):
        for project in self:
            html = """
                <div style="margin-bottom: 30px;">
                    <div style="font-size: 18px; margin-bottom: 10px; color: #444; border-bottom: 2px solid #ddd; padding-bottom: 5px;">الجدول الزمني (Timeline)</div>
                    <div style="border: 1px solid #ddd; border-radius: 10px; padding: 15px; background: #fefefe; overflow-x: auto;">
            """

            html += """
                <div style="display: flex; justify-content: space-between; font-size: 13px; color: #999; margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 10px; min-width: 900px;">
            """

            arabic_months = [
                "", "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
                "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"
            ]

            today = datetime.today()
            start_month = today.month
            year = today.year

            day_patterns = {
                1: [1, 10, 20],
                2: [1, 10, 20],
                3: [1, 15, 30]
            }

            dates = []
            for i in range(3):
                month = (start_month + i - 1) % 12 + 1
                current_year = year + ((start_month + i - 1) // 12)
                day_list = day_patterns.get(i + 1, [1, 10, 20])
                for day in day_list:
                    if day <= calendar.monthrange(current_year, month)[1]:
                        dates.append(f"{day} {arabic_months[month]}")

            for d in dates:
                html += f"<div style='width: 10%; text-align: center;'>{d}</div>"
            html += "</div>"

            for task in project.task_ids:
                if not task.date_deadline:
                    continue
                deadline = task.date_deadline.strftime('%d %b')
                html += f"""
                    <div style="display: flex; align-items: center; margin-bottom: 15px; min-width: 900px;">
                        <div style="width: 140px; font-size: 14px; color: #444;">{task.name}</div>
                        <div style="height: 30px; background-color: #00cec9; color: white; border-radius: 6px; padding: 6px 10px; font-size: 13px; margin-right: 12%; width: 18%;">
                            حتى {deadline}
                        </div>
                    </div>
                """

            html += "</div></div>"
            project.timeline_html = html

    customer_invoice_count = fields.Integer(
        string="فواتير العملاء",
        compute='_compute_customer_invoice_count',
        store=True
    )

    def _compute_customer_invoice_count(self):
        AccountMove = self.env['account.move']
        for project in self:
            # نبحث عن كل الفواتير من نوع Customer Invoice (out_invoice) المرتبطة بالمشروع
            project.customer_invoice_count = AccountMove.search_count([
                ('move_type', '=', 'out_invoice'),
                ('project_id', '=', project.id)
            ])




    
    @api.depends('date_start', 'date', 'crm_lead_ids.contract_files_count', 'crm_lead_ids.purchase_files_count')
    def _compute_project_statistics(self):
        """حساب الإحصائيات الذكية للمشروع"""
        from datetime import date
        
        for project in self:
            today = date.today()
            
            # 1. عمر المشروع (من تاريخ الإنشاء حتى تاريخ الانتهاء)
            if project.date_start and project.date:
                project.project_age_days = (project.date - project.date_start).days
            elif project.date_start:
                # إذا لم يكن هناك تاريخ انتهاء، احسب من الإنشاء حتى اليوم
                project.project_age_days = (today - project.date_start).days
            else:
                project.project_age_days = 0
            
            # 2. الأيام المتبقية (لا تظهر أرقام سالبة)
            if project.date:
                days_calc = (project.date - today).days
                project.days_remaining = max(0, days_calc)  # لا تظهر أرقام سالبة، 0 كحد أدنى
                project.is_overdue = days_calc < 0
            else:
                project.days_remaining = 0
                project.is_overdue = False
            
            # 3. حالة العقد (من الفرص المرتبطة)
            # المشروع مربوط بفرصة، والفرصة فيها ملفات عقود/أوامر شراء
            contract_count = 0
            po_count = 0
            
            for lead in project.crm_lead_ids:
                contract_count += lead.contract_files_count
                po_count += lead.purchase_files_count
            
            # إذا فيه عقد واحد أو أكثر أو أمر شراء = أخضر
            # إذا لا يوجد = أحمر
            if contract_count > 0 or po_count > 0:
                project.has_contract = True
                project.contract_status_color = 'success'  # أخضر
                project.project_status_message = f"✓ يوجد {contract_count} عقد و {po_count} أمر شراء"
            else:
                project.has_contract = False
                project.contract_status_color = 'danger'  # أحمر
                project.project_status_message = "⚠ لا يوجد عقد أو أمر شراء"
            
            # 4. التحذيرات
            warnings = []
            if not project.has_contract:
                warnings.append("لا يوجد عقد")
            if project.is_overdue:
                warnings.append("متأخر عن الموعد")
            if project.days_remaining > 0 and project.days_remaining <= 7:
                warnings.append("سينتهي خلال أسبوع")
            
            project.has_warning = len(warnings) > 0

