from odoo import api, fields, models



class ProposalStages(models.Model):
    _name = 'proposal.stages'


    name = fields.Char()

class ProposalLossReason(models.Model):
    _name = 'proposal.loss.reason'

    reason = fields.Char()