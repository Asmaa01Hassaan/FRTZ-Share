from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ProjectProject(models.Model):
    _inherit = 'project.project'

    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
        readonly=True
    )

    quick_total_budget = fields.Monetary(
        string="Total Budget",
        currency_field='company_currency_id',
        compute='_compute_quick_budget',
        store=False,
    )
    quick_total_spent = fields.Monetary(
        string="Total Spent",
        currency_field='company_currency_id',
        compute='_compute_quick_budget',
        store=False,
    )
    quick_remaining = fields.Monetary(
        string="Remaining",
        currency_field='company_currency_id',
        compute='_compute_quick_budget',
        store=False,
    )
    quick_utilization = fields.Float(
        string="Utilization %",
        compute='_compute_quick_budget',
        store=False,
    )
    quick_overspent = fields.Boolean(
        string="Overspent?",
        compute='_compute_quick_budget',
        store=False,
    )

    # Project Charter fields
    project_charter_sequence = fields.Char(
        string="Project Charter Number",
        readonly=True,
        copy=False,
        help="Unique sequence number for the project charter document"
    )
    project_charter_url = fields.Char(
        string="Project Charter URL",
        compute='_compute_project_charter_url',
        readonly=True,
        help="URL to access the project charter PDF report"
    )
    project_objective = fields.Html(
        string="Project Objective",
        help="Project objectives and goals",
        sanitize_style=True
    )
    project_scope = fields.Html(
        string="Project Scope",
        help="Project scope and boundaries",
        sanitize_style=True
    )

    # مفيش @api.depends هنا عشان مافيش حقل ثابت نعلّق عليه،
    # والحقول غير مخزّنة وبالتالي هتتحسب Live عند القراءة.
    def _compute_quick_budget(self):
        for project in self:
            allocated = 0.0  # = الميزانية
            spent_pos = 0.0  # = المصروف (قيمة موجبة)
            try:
                items = project._get_budget_items(with_action=False) or {}
                totals = items.get('total') or {}
                allocated = totals.get('allocated') or 0.0
                # نفس إشارة ProjectUpdate: cost = -spent  → إذن المصروف الموجب = -(spent)
                spent_pos = -(totals.get('spent') or 0.0)
            except Exception:
                allocated = 0.0
                spent_pos = 0.0

            remaining = allocated - spent_pos
            utilization = (spent_pos / allocated) * 100.0 if allocated else 0.0

            project.quick_total_budget = allocated
            project.quick_total_spent = spent_pos
            project.quick_remaining = remaining
            project.quick_utilization = round(utilization, 2)
            project.quick_overspent = spent_pos > allocated

    def _compute_project_charter_url(self):
        """Compute the URL for the project charter PDF report"""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        report_action = self.env.ref('crm_task_link.action_report_project_charter', raise_if_not_found=False)
        
        for project in self:
            if report_action and project.id:
                # URL to generate and download the PDF report
                project.project_charter_url = f"{base_url}/report/pdf/crm_task_link.report_project_charter/{project.id}"
            else:
                project.project_charter_url = False

    def _ensure_charter_sequence(self):
        """Ensure project charter sequence is generated"""
        for project in self:
            if not project.project_charter_sequence:
                sequence_code = 'project.charter.sequence'
                project.project_charter_sequence = self.env['ir.sequence'].next_by_code(sequence_code) or _('New')

    def action_view_project_charter(self):
        """Open the project charter PDF report"""
        self.ensure_one()
        
        # Generate sequence number if not exists
        self._ensure_charter_sequence()
        
        return {
            'type': 'ir.actions.report',
            'report_name': 'crm_task_link.report_project_charter',
            'report_type': 'qweb-pdf',
            'res_model': 'project.project',
            'res_id': self.id,
            'context': self.env.context,
        }
