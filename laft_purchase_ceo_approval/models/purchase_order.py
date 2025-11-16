from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # Add our two states (don’t redefine the original list)
    state = fields.Selection(
        selection_add=[
            ('draft1', 'Draft (Pre-RFQ)'),
            ('ceo', 'CEO review'),
        ],
        ondelete={'draft1': 'set default', 'ceo': 'set default'},
        default='draft1',          # start in our pre-RFQ draft
        tracking=True,
    )
    # quick_total_budget = fields.Monetary(
    #     string="Total Budget",
    #     related='project_id.quick_total_budget',
    #     store=False,
    # )
    # quick_total_spent = fields.Monetary(
    #     string="Total Spent",
    #     related='project_id.quick_total_spent',
    #     store=False,
    # )
    # quick_remaining = fields.Monetary(
    #     string="Remaining",
    #     related='project_id.quick_remaining',
    #     store=False,
    # )
    # quick_utilization = fields.Monetary(
    #     string="Utilization %",
    #     related='project_id.quick_utilization',
    #     store=False,
    # )


    # -------- helpers (email + url) --------
    def _group_partners(self, xmlid):
        group = self.env.ref(xmlid, raise_if_not_found=False)
        return (group.users.mapped('partner_id').filtered(lambda p: p.email)) if group else self.env['res.partner']

    def _notify_group(self, xmlid, subject, body, subscribe=True):
        partners = self._group_partners(xmlid)
        if not partners:
            return
        if subscribe:
            self.message_subscribe(partner_ids=partners.ids)
        for rec in self:
            rec.message_post(
                subject=subject,
                body=body,
                partner_ids=partners.ids,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
                email_layout_xmlid='mail.mail_notification_light',
            )

    def _notify_creator(self, subject, body):
        for rec in self:
            creator = rec.create_uid.partner_id
            if creator and creator.email:
                rec.message_subscribe(partner_ids=[creator.id])
                rec.message_post(
                    subject=subject,
                    body=body,
                    partner_ids=[creator.id],
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                    email_layout_xmlid='mail.mail_notification_light',
                )

    def _record_url(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base}/web#id={self.id}&model=purchase.order&view_type=form"

    # -------- transitions --------
    def action_submit_to_ceo(self):
        for po in self:
            if po.state != 'draft1':
                raise UserError(_("Only pre-RFQ Draft can be submitted to CEO."))
            po.write({'state': 'ceo'})
            po._notify_group(
                'laft_purchase_ceo_approval.group_ceo_approver',
                subject=_("RFQ requires CEO approval"),
                body=_("""A purchase order requires your approval.
                       Open Order \n\n '%s'""") % po._record_url(),


            )

    def action_ceo_approve(self):
        if not self.env.user.has_group('laft_purchase_ceo_approval.group_ceo_approver'):
            raise AccessError(_("You don't have permissions to approve as CEO."))
        for po in self:
            if po.state != 'ceo':
                raise UserError(_("Only orders in CEO review can be approved."))
            # hand over to stock RFQ state; default buttons/flow work as usual
            po.write({'state': 'draft'})
            po._notify_creator(
                subject=_("CEO approved your RFQ"),
                body=_("Your RFQ was approved by CEO.\n Open Order \n  '%s' ") % po._record_url(),
            )

    def action_ceo_reject(self):
        if not self.env.user.has_group('laft_purchase_ceo_approval.group_ceo_approver'):
            raise AccessError(_("You don't have permissions to reject as CEO."))
        for po in self:
            if po.state != 'ceo':
                raise UserError(_("Only orders in CEO review can be rejected."))
            po.write({'state': 'draft1'})
            po._notify_creator(
                subject=_("CEO rejected your RFQ"),
                body=_("Your RFQ was rejected by CEO and returned to Pre-RFQ Draft.Open Order '%s'")
                     % po._record_url(),
            )
