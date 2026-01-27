from odoo import models, fields

class LaptopRecords(models.Model):
    _name="laptop.records"
    _description="Laptop Records"

    employee_id = fields.Many2one('hr.employee', string="Employee")
    brand = fields.Char(string="Brand")
    model = fields.Char(string="Model")
    serial_number = fields.Char(string="Serial Number")
    issue_date = fields.Date(string="Issue Date")
    
    
class CarRecords(models.Model):
    _name="car.records"
    _description="Car Records"

    employee_id = fields.Many2one('hr.employee', string="Employee")
    brand = fields.Char(string="Brand")
    model = fields.Char(string="Model")
    plate_number = fields.Char(string="Plate Number")
    vin_number = fields.Char(string="VIN Number")
    issue_date = fields.Date(string="Issue Date")