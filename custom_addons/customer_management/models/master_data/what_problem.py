from odoo import models, fields


class WhatProblem(models.Model):
    _name = "what.problem"
    _description = "Problem"
    _order = "name asc"

    name = fields.Char(string="Problem")
