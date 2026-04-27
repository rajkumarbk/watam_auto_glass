from odoo import models, fields, api


class DepartmentInherit(models.Model):
    _inherit = "hr.department"

    department_sequence = fields.Char(string="Department Sequence", required=True)
