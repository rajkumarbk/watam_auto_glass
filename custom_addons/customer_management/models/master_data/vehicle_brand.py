from odoo import models, fields


class VehicleBrand(models.Model):
    _name = "vehicle.brand"
    _description = "Vehicle Brand"
    _order = "name asc"

    name = fields.Char(required=True, string="Brand Name", help="Brand of the vehicle", translate=True)