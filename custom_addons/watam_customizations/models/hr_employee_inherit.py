# -*- coding: utf-8 -*-
from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    passport_expiry = fields.Date(string="Passport Expiry Date")
    
    laptop_records_ids = fields.One2many('laptop.records', 'employee_id', string="Laptop Records")
    car_records_ids = fields.One2many('car.records', 'employee_id', string="Car Records")

    is_laptop=fields.Boolean(string="Laptop")
    laptop_brand=fields.Char(string="Laptop Brand")
    laptop_model=fields.Char(string="Laptop Model")
    laptop_serial_number=fields.Char(string="Laptop Serial Number")
    laptop_issue_date=fields.Date(string="Laptop Issue Date")
    
    is_car=fields.Boolean(string="Car")
    car_brand=fields.Char(string="Car Brand")
    car_model=fields.Char(string="Car Model")
    car_plate_number=fields.Char(string="Car Plate Number")
    car_issue_date=fields.Date(string="Car Issue Date")
    car_vin_number=fields.Char(string="Car VIN Number")
    
class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    passport_expiry = fields.Date(string="Passport Expiry Date")

    laptop_records_ids = fields.One2many('laptop.records', 'employee_id', string="Laptop Records")
    car_records_ids = fields.One2many('car.records', 'employee_id', string="Car Records")
    is_laptop=fields.Boolean(string="Laptop", default=False)
    laptop_brand=fields.Char(string="Laptop Brand")
    laptop_model=fields.Char(string="Laptop Model")
    laptop_serial_number=fields.Char(string="Laptop Serial Number")
    laptop_issue_date=fields.Date(string="Laptop Issue Date")
    
    is_car=fields.Boolean(string="Car", default=False)
    car_brand=fields.Char(string="Car Brand")
    car_model=fields.Char(string="Car Model")
    car_plate_number=fields.Char(string="Car Plate Number")
    car_issue_date=fields.Date(string="Car Issue Date")
    car_vin_number=fields.Char(string="Car VIN Number")