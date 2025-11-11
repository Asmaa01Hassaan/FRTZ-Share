from odoo import api, fields, models, _

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
