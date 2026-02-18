from odoo import api, fields, models,_


class ProjectProposal(models.Model):
    _name = 'project.proposal'
    _description = 'Project Proposal Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    name = fields.Char(string='New', readonly='True', default=lambda self: 'New')
    partner_id = fields.Many2one('res.partner', string='Partner')
    commercial_partner = fields.Char(string='Commercial Partner')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    currency_id = fields.Many2one('res.currency')
    project_id = fields.Many2one('project.project')
    proposal_type_id = fields.Many2one('crm.extension', string='Type')

    profitability_responsible_id = fields.Many2one('res.users', string="Profitability Responsible")
    sales_responsible_id = fields.Many2one('res.users', string="Sales Responsible")
    finance_responsible_id = fields.Many2one('res.users', string="Finance Responsible")

    is_completed = fields.Boolean(string="Is Completed")

    proposal_date = fields.Date()
    proposal_submission_date = fields.Date()
    expected_closing_date = fields.Date()
    project_start_date = fields.Date()
    project_end_date = fields.Date()
    contract_date = fields.Date()


    expected_revenue = fields.Float(string="Expected Revenue")
    expected_cost = fields.Float(string="Expected Cost")
    expected_margin = fields.Float(string="Expected Margin")
    expected_margin_percentage = fields.Float(string="Expected Margin %")

    contracted_revenue = fields.Float(string="Contracted Revenue")
    contracted_cost = fields.Float(string="Contracted Cost")
    contracted_margin = fields.Float(string="Contracted Margin")
    contracted_margin_percentage = fields.Float(string="Contracted Margin %")

    actual_revenue = fields.Float(string="Actual Revenue")
    actual_cost = fields.Float(string="Actual Cost")
    actual_margin = fields.Float(string="Actual Margin")
    actual_margin_percentage = fields.Float(string="Actual Margin %")

    financial_progress = fields.Integer()
    project_progress = fields.Integer()

    product = fields.Char(readonly='True')
    quantity = fields.Float(readonly='True')
    cost_price = fields.Float(readonly='True')

    purchase_count = fields.Integer(compute='_compute_counts')
    sale_count = fields.Integer(compute='_compute_counts')
    invoice_count = fields.Integer(compute='_compute_counts')
    bill_count = fields.Integer(compute='_compute_counts')
    entry_count = fields.Integer(compute='_compute_counts')
    project_count = fields.Integer(compute='_compute_counts')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('kick_off', 'Kick Off'),
        ('proposal_build_up', 'Proposal Build Up'),
        ('negotiation', 'Negotiation'),
        ('pending', 'Pending Proposal'),
        ('won_ongoing', 'Won/Ongoing'),
        ('won_done', 'Won/Done'),
        ('collection', 'Collection'),
        ('won', 'Won'),
        ('lost', 'Lost'),
    ], string='Status', default='draft')



    def _compute_counts(self):
        for rec in self:
            rec.purchase_count = self.env['purchase.order'].search_count([('proposal_id', '=', rec.id)])
            rec.sale_count = self.env['sale.order'].search_count([('proposal_id', '=', rec.id)])
            rec.invoice_count = self.env['account.move'].search_count(
                [('proposal_id', '=', rec.id), ('move_type', '=', 'out_invoice')])
            rec.bill_count = self.env['account.move'].search_count(
                [('proposal_id', '=', rec.id), ('move_type', '=', 'in_invoice')])
            rec.entry_count = self.env['account.move'].search_count(
                [('proposal_id', '=', rec.id), ('move_type', '=', 'entry')])
            rec.project_count = self.env['project.project'].search_count([('proposal_id', '=', rec.id)])


    def action_view_purchase(self):
        return {
            'name': 'Purchase Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('proposal_id', '=', self.id)],
        }

    def action_view_sales(self):
        self.ensure_one()
        return {
            'name': 'Sales Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('proposal_id', '=', self.id)],
            'context': {'default_proposal_id': self.id},
        }

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'name': 'Invoices',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('proposal_id', '=', self.id), ('move_type', '=', 'out_invoice')],
            'context': {
                'default_proposal_id': self.id,
                'default_move_type': 'out_invoice',
            },
        }

    def action_view_bills(self):
        self.ensure_one()
        return {
            'name': 'Bills',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('proposal_id', '=', self.id), ('move_type', '=', 'in_invoice')],
            'context': {
                'default_proposal_id': self.id,
                'default_move_type': 'in_invoice',
            },
        }

    def action_view_entries(self):
        self.ensure_one()
        return {
            'name': 'Journal Entries',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('proposal_id', '=', self.id), ('move_type', '=', 'entry')],
            'context': {
                'default_proposal_id': self.id,
                'default_move_type': 'entry',
            },
        }

    def action_view_projects(self):
        self.ensure_one()
        return {
            'name': 'Projects',
            'type': 'ir.actions.act_window',
            'res_model': 'project.project',
            'view_mode': 'list,form',
            'domain': [('proposal_id', '=', self.id)],
            'context': {
                'default_proposal_id': self.id,
            },
        }




    def action_kick_off(self):
        self.state = 'kick_off'

    def action_proposal_build_up(self):
        self.state = 'proposal_build_up'

    def action_negotiation(self):
        self.state = 'negotiation'

    def action_pending(self):
        self.state = 'pending'

    def action_won_ongoing(self):
        self.state = 'won_ongoing'

    def action_won_done(self):
        self.state = 'won_done'

    def action_collection(self):
        self.state = 'collection'

    def action_set_won(self):
        self.state = 'won'

    def action_set_lost(self):
        self.state = 'lost'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('project.proposal') or _('New')
        return super(ProjectProposal, self).create(vals_list)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    proposal_id = fields.Many2one('project.proposal', string='Proposal Reference')

class AccountMove(models.Model):
    _inherit = 'account.move'

    proposal_id = fields.Many2one('project.proposal', string='Proposal Reference')

class SalesOrder(models.Model):
    _inherit = 'sale.order'

    proposal_id = fields.Many2one('project.proposal', string='Proposal Reference')


class ProjectProject(models.Model):
    _inherit = 'project.project'

    proposal_id = fields.Many2one('project.proposal', string='Proposal Reference')
