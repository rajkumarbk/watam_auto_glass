from odoo import fields, models, api


class HrJob(models.Model):
    _inherit = "hr.job"

    department_id = fields.Many2one(
        "hr.department",
        string="Select Department",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
