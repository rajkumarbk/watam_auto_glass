# -*- coding: utf-8 -*-
from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    passport_expiry = fields.Date(string="Passport Expiry Date")
