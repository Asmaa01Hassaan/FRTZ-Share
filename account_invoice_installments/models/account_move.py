from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = "account.move"

    payment_type = fields.Selection(
        [
            ("regular", _("Regular")),
            ("irregular", _("Irregular")),
            ("immediate", _("Immediate")),
        ],
        string=_("Payment plan"),
        default="immediate",
        tracking=True,
        copy=False,
    )

    first_payment_type = fields.Selection(
        [
            ("fixed", _("Fixed")),
            ("percent", _("Percent")),
        ],
        string=_("payment Type"),
        tracking=True,
        copy=False,
    )

    first_payment_value = fields.Monetary(
        string=_("First payment value"),
        currency_field="currency_id",
        tracking=True,
        copy=False,
    )

    first_payment_percent = fields.Float(
        string=_("First payment (%)"),
        digits=(16, 4),
        tracking=True,
        copy=False,
    )

    installment_count = fields.Integer(
        string=_("Installment count"),
        tracking=True,
        copy=False,
    )

    @api.depends("partner_id", "payment_type")
    def _compute_invoice_payment_term_id(self):
        irregular = self.filtered(lambda m: m.payment_type == "irregular")
        (self - irregular).invoice_payment_term_id = False
        super(AccountMove, irregular)._compute_invoice_payment_term_id()

    @api.onchange("payment_type")
    def _onchange_invoice_payment_type(self):
        for move in self:
            if move.payment_type != "irregular":
                move.invoice_payment_term_id = False

    @api.onchange("first_payment_type")
    def _onchange_first_payment_type(self):
        for move in self:
            if move.first_payment_type == "fixed":
                move.first_payment_percent = 0.0
            elif move.first_payment_type == "percent":
                move.first_payment_value = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("payment_type", "immediate") != "irregular":
                vals["invoice_payment_term_id"] = False
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        if vals.get("payment_type") is not None and vals.get("payment_type") != "irregular":
            vals["invoice_payment_term_id"] = False
        return super().write(vals)
