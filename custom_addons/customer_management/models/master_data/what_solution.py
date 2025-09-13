from odoo import models, fields


class WhatSolution(models.Model):
    _name = "what.solution"
    _description = "solution"
    _order = "name asc"

    name = fields.Char(string="solution")
    problem_id = fields.Many2one("what.problem", string="Problem")
