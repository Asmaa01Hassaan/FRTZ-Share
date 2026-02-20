from odoo import api, fields, models


class ProjectProposalLostWizard(models.TransientModel):
    _name = "project.proposal.lost.wizard"
    _description = "Wizard to select lost reason and add note"

    proposal_id = fields.Many2one('project.proposal', string="Proposal")
    lost_reason_id = fields.Many2one('proposal.loss.reason', string="Lost Reason", required=True)
    lost_note = fields.Text("Note")

    def action_confirm_lost(self):
        self.proposal_id.state = 'lost'
        self.proposal_id.lost_reason_id = self.lost_reason_id
        self.proposal_id.lost_note = self.lost_note
        return {'type': 'ir.actions.act_window_close'}
