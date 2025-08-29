from odoo import models, fields


class ManufacturedYear(models.Model):
    _name = "manufactured.year"
    _description = "Vehicle year"
    _order = "name desc"

    name = fields.Char(required=True, string="Manufactured Year")
