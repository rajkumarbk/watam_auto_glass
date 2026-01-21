# -*- coding: utf-8 -*-
from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.contract"

    crn = fields.Char(string="CRN")
    joined_date = fields.Date(string="Joined Date")
