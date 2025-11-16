from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError


class AccountMove(models.Model):
    _inherit = "account.move"
    quick_total_budget = fields.Monetary(
        string="Total Budget",
        related='project_id.quick_total_budget',
        store=False,
    )
    quick_total_spent = fields.Monetary(
        string="Total Spent",
        related='project_id.quick_total_spent',
        store=False,
    )
    quick_remaining = fields.Monetary(
        string="Remaining",
        related='project_id.quick_remaining',
        store=False,
    )
    # quick_utilization = fields.Monetary(
    #     string="Utilization %",
    #     related='project_id.quick_utilization',
    #     store=False,
    # )
    approval_state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("pm_review", "Project Director"),
            ("bd_review", "Business Development Review"),
            ("finance_pending", "Finance Team Review"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Approval State",
        default="draft",
        tracking=True,
        copy=False,
    )
    rejection_reason = fields.Text(string="Rejection Reason", copy=False)

    # --- helpers
    def _group_partners(self, xmlid):
        """Return partners (with email) of users in a given group xmlid."""
        group = self.env.ref(xmlid, raise_if_not_found=False)
        if not group:
            return self.env['res.partner']
        return group.users.mapped('partner_id').filtered(lambda p: p.email)

    def _notify_group(self, xmlid, subject, body, force_follow=True):
        """Post a message to the record and email the group partners."""
        partners = self._group_partners(xmlid)
        if not partners:
            return
        # Make sure recipients follow the document so they get notifications
        if force_follow:
            self.message_subscribe(partner_ids=partners.ids)
        # Post one message per record (keeps chatter clean)
        for rec in self:
            rec.message_post(
                subject=subject,
                body=body,
                partner_ids=partners.ids,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
                email_layout_xmlid='mail.mail_notification_light',  # nice email layout
            )

    def _notify_requester(self, subject, body):
        """Notify the bill creator on this move."""
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

    def _check_group(self, xmlid):
        if not self.env.user.has_group(xmlid):
            raise AccessError(_("You don't have permissions for this step."))

    def _ensure_vendor_bill(self):
        # apply only to vendor bills/credit notes
        illegal = self.filtered(lambda m: m.move_type not in ("in_invoice", "in_refund"))
        if illegal:
            raise UserError(_("This approval flow applies only to Vendor Bills/Refunds."))

    # --- transitions
    def action_send_to_pm_review(self):
        self._ensure_vendor_bill()
        for move in self:
            if move.approval_state != "draft":
                raise UserError(_("Only Draft bills can be sent to PM Review."))
            move.write({"approval_state": "pm_review", "rejection_reason": False})
            # Notify PM group: they need to review
            self._notify_group(
                "laft_vendor_bill_approval.group_bill_pm",
                subject=_("Bill needs PM Review"),
                body=_("A vendor bill requires your review and approval to proceed to BD."),
            )

    def action_pm_approve(self):
        self._check_group("laft_vendor_bill_approval.group_bill_pm")
        self._ensure_vendor_bill()
        for move in self:
            if move.approval_state != "pm_review":
                raise UserError(_("Bill must be in PM Review to approve."))
            move.write({"approval_state": "bd_review", "rejection_reason": False})
            # Notify BD group: they are next
            self._notify_group(
                "laft_vendor_bill_approval.group_bill_bd",
                subject=_("Bill moved to BD Review"),
                body=_("PM approved the bill. Please review to move it to Finance."),
            )

    def action_pm_reject(self, reason=False):
        self._check_group("laft_vendor_bill_approval.group_bill_pm")
        self._ensure_vendor_bill()
        if not reason and self._context.get("reject_reason"):
            reason = self._context["reject_reason"]
        if not reason:
            raise UserError(_("Please provide a rejection reason."))
        for move in self:
            move.write({"approval_state": "rejected", "rejection_reason": reason})
            # Inform the requester
            self._notify_requester(
                subject=_("Bill Rejected by PM"),
                body=_("Reason: %s") % (reason,),
            )

    def action_bd_approve(self):
        self._check_group("laft_vendor_bill_approval.group_bill_bd")
        self._ensure_vendor_bill()
        for move in self:
            if move.approval_state != "bd_review":
                raise UserError(_("Bill must be in BD Review to approve."))
            move.write({"approval_state": "finance_pending", "rejection_reason": False})
            # Notify Finance group
            self._notify_group(
                "laft_vendor_bill_approval.group_bill_finance",
                subject=_("Bill moved to Finance Review"),
                body=_("BD approved the bill. Please review and post when ready."),
            )

    def action_bd_reject(self, reason=False):
        self._check_group("laft_vendor_bill_approval.group_bill_bd")
        self._ensure_vendor_bill()
        reason = reason or self._context.get("reject_reason")
        if not reason:
            raise UserError(_("Please provide a rejection reason."))
        for move in self:
            move.write({"approval_state": "rejected", "rejection_reason": reason})
            self._notify_requester(
                subject=_("Bill Rejected by BD"),
                body=_("Reason: %s") % (reason,),
            )

    def action_finance_approve(self):
        self._check_group("laft_vendor_bill_approval.group_bill_finance")
        self._ensure_vendor_bill()
        for move in self:
            if move.approval_state != "finance_pending":
                raise UserError(_("Bill must be in Finance Review to approve."))
            move.write({"approval_state": "approved", "rejection_reason": False})
            # optional: auto-post when fully approved
            # if move.state == 'draft':
            #     move.action_post()
            # Notify requester that it’s fully approved
            self._notify_requester(
                subject=_("Bill Approved"),
                body=_("Your vendor bill has completed all approval steps."),
            )

    def action_finance_reject(self, reason=False):
        self._check_group("laft_vendor_bill_approval.group_bill_finance")
        self._ensure_vendor_bill()
        reason = reason or self._context.get("reject_reason")
        if not reason:
            raise UserError(_("Please provide a rejection reason."))
        for move in self:
            move.write({"approval_state": "rejected", "rejection_reason": reason})
            # Inform the requester
            self._notify_requester(
                subject=_("Bill Rejected by Finance"),
                body=_("Reason: %s") % (reason,),
            )
