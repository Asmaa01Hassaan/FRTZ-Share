from odoo import api, fields, models,_



class ProposalStages(models.Model):
    _name = 'proposal.stages'
    _description = "Project Proposal Stage"
    _order = "sequence, id"

    name = fields.Char("Stage Name", required=True)
    sequence = fields.Integer("Sequence", default=10)
    fold = fields.Boolean("Folded in Kanban")
    color = fields.Integer("Color")

class ProposalLossReason(models.Model):
    _name = 'proposal.loss.reason'

    name = fields.Char(string='Description')

    def action_lost_leads(self):
        return {
            'name': _('Lost'),
            'view_mode': 'list,form',
            'domain': [('lost_reason_id', 'in', self.ids)],
            'res_model': 'proposal.loss.reason',
            'type': 'ir.actions.act_window',
            'context': {'create': False, 'active_test': False},
        }