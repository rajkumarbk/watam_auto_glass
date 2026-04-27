from odoo import fields, models, api


class HrEmployee(models.Model):
    _inherit = "hr.contract"

    crn = fields.Char(string="CRN")
    employee_parent_id = fields.Many2one(
        "hr.employee",
        string="Direct Manager",
        related="employee_id.parent_id",
        store=True,
        readonly=True,
    )
    contract_duration = fields.Selection(
        [
            ("3", "3 Months"),
            ("6", "6 Months"),
            ("12", "12 Months"),
            ("24", "24 Months"),
            ("36", "36 Months"),
        ],
        string="Contract Duration",
        default="12",
    )
    probation_period = fields.Selection(
        [
            ("3", "3 Months"),
            ("6", "6 Months"),
            ("12", "12 Months"),
        ],
        string="Probation Period",
        default="3",
    )
    reason_for_termination = fields.Many2one(
        "hr.departure.reason", string="Reason for termination"
    )

    joined_date = fields.Date(
        string="Hiring Date", compute="_get_employee_data", store=True, readonly=True
    )
    work_location = fields.Many2one(
        "hr.work.location",
        string="Work Location",
    )

    @api.depends("employee_id", "employee_id.join_date")
    def _get_employee_data(self):
        for contract in self:
            contract.joined_date = (
                contract.employee_id.join_date if contract.employee_id else False
            )
