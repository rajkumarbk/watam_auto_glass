from odoo import models, fields

class VehicleModel(models.Model):
    _name = "vehicle.model"
    _description = "Vehicle Model"
    _order = "name asc"

    name = fields.Char(required=True, string="Model Name", help="Model of the vehicle", translate=True)
    brand_id = fields.Many2one("vehicle.brand", string="Vehicle Brand", required=True)
    manufactured_year_id = fields.Many2many('manufactured.year' , string="Manufactured Year", help="Year the vehicle was manufactured")