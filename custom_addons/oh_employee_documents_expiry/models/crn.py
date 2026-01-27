from odoo import models, fields


class CrnMaster(models.Model):
    _name = "crn.master"
    _description = "CRN Master"

    name = fields.Char(string="CRN", required=True)

    _sql_constraints = [("crn_unique", "unique(name)", "CRN must be unique.")]
