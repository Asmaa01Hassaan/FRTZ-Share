from odoo import fields, models


class ContactDivision(models.Model):
    _name = "contact.division"
    _description = "Contact Division"
    _order = "id desc"
    _rec_name = "department"

    partner_id = fields.Many2one(
        "res.partner",
        string="Contact",
        required=True,
        ondelete="cascade",
        index=True,
    )
    department = fields.Char(string="Department", required=True)
    reference = fields.Char(string="Reference")

    def name_get(self):
        res = []
        for rec in self:
            name = rec.department or ""
            if rec.reference:
                name = f"{name} ({rec.reference})" if name else rec.reference
            res.append((rec.id, name or f"Division #{rec.id}"))
        return res


