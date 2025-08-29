from odoo import models, fields


class GlassDestination(models.Model):
    _name = "vehicle.glass"
    _description = "Glass Destination"
    _order = "name asc"

    name = fields.Char(
        required=True, string="Glass Name", help="Glass Name", translate=True
    )
