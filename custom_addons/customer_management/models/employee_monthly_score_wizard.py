from odoo import api, fields, models


class EmployeeMonthlyScoreWizard(models.TransientModel):
    _name = "employee.monthly.score.wizard"
    _description = "Generate Employee Monthly Scores"

    month_date = fields.Date(
        string="Month", required=True,
        default=fields.Date.context_today,
        help="Any date within the target month",
    )
    branch_ids = fields.Many2many(
        "res.company", string="Branches",
        help="Leave empty to generate for all branches",
    )

    def action_generate(self):
        self.ensure_one()
        created = self.env["employee.monthly.score"]
        if self.branch_ids:
            all_branches = self.branch_ids | self.branch_ids.mapped("child_ids")
        else:
            all_branches = self.env["res.company"].search([])
        for branch in all_branches:
            created |= self.env["employee.monthly.score"].generate_monthly_scores(
                self.month_date, branch.id
            )
        return {
            "type": "ir.actions.act_window",
            "name": "Employee of the Month",
            "res_model": "employee.monthly.score",
            "view_mode": "list,form",
            "domain": [("id", "in", created.ids)] if created else [],
            "target": "current",
        }