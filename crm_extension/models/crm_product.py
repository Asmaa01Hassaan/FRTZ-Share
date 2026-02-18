from odoo import models, fields, api


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    product_line_ids = fields.One2many('crm.product.line', 'lead_id', string='Product Lines')
    opportunity_type_id = fields.Many2one('crm.extension',string='Opportunity Type')


    def action_create_proposal(self):
        self.ensure_one()
        analytic_account = self.env['account.analytic.account'].create({
            'name': self.name,
            'plan_id': self.env.ref('analytic.analytic_plan_projects').id,
            'partner_id': self.partner_id.id,
        })
        return {
            'name': 'Create Project Proposal',
            'type': 'ir.actions.act_window',
            'res_model': 'project.proposal',
            'view_mode': 'form',
            'view_id': self.env.ref('crm_extension.view_project_proposal_form').id,
            'target': 'new',
            'context': {
                'default_proposal_type_id': self.opportunity_type_id.id,
                'default_product': self.product_line_ids.product_id.name,
                'default_quantity':self.product_line_ids.qty,
                'default_analytic_account_id': analytic_account.id,  # الربط هنا
                'default_cost_price':self.product_line_ids.cost_price
            }
        }


class CrmProductLine(models.Model):
    _name = 'crm.product.line'
    _description = 'CRM Product Lines'

    lead_id = fields.Many2one('crm.lead', string='Lead Reference', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product')

    cost_price = fields.Float(related='product_id.standard_price', string='Cost', readonly=True)
    qty = fields.Float(string='Quantity', default=1.0)
