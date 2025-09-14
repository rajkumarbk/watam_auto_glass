from odoo import models, fields, api


class ServiceOption(models.Model):
    _name = "service.option"
    _description = "Service Option"

    name = fields.Char(string="Service Option Name", required=True)
