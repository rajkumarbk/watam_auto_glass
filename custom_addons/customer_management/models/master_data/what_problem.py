from odoo import models, fields


class WhatProblem(models.Model):
    _name = "what.problem"
    _description = "Problem"
    _order = "name asc"

    name = fields.Char(string="Problem")
    solution_ids = fields.One2many('what.solution', 'problem_id', string="Solutions")
