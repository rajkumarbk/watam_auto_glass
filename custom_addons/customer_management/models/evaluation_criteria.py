from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta


class EvaluationCriteria(models.Model):
    _name = "evaluation.criteria"
    _description = "Evaluation Criteria"
    _rec_name = "date"
    _order = "date desc"

    branch_id = fields.Many2one(
        "res.company",
        string="Branch",
        default=lambda self: self.env.company,
    )
    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
        required=True,
        domain="[('company_id', '=', branch_id)]",
    )
    date = fields.Date(string="Date", default=fields.Date.context_today)
    attendance_punctuality = fields.Float(
        string="Attendance and Punctuality (20)", default=0.0
    )
    work_quality = fields.Float(
        string="Work Quality and Installation Accuracy (30)", default=0.0
    )
    customer_interaction = fields.Float(string="Customer Interaction (20)", default=0.0)
    proactivity_initiative = fields.Float(
        string="Proactivity and Initiative (10)", default=0.0
    )
    uniform_safety = fields.Float(
        string="Adherence to Uniform and Safety Regulations (10)", default=0.0
    )
    reporting = fields.Float(
        string="Reporting Observations and Malfunctions (10)", default=0.0
    )

    total_score = fields.Float(
        string="Total Score", compute="_compute_total", store=True
    )

    @api.depends(
        "attendance_punctuality",
        "work_quality",
        "customer_interaction",
        "proactivity_initiative",
        "uniform_safety",
        "reporting",
    )
    def _compute_total(self):
        for record in self:
            record.total_score = (
                record.attendance_punctuality
                + record.work_quality
                + record.customer_interaction
                + record.proactivity_initiative
                + record.uniform_safety
                + record.reporting
            )

    @api.constrains(
        "attendance_punctuality",
        "work_quality",
        "customer_interaction",
        "proactivity_initiative",
        "uniform_safety",
        "reporting",
    )
    def _check_max_points(self):
        for record in self:
            if record.attendance_punctuality > 20:
                raise ValidationError(
                    "Attendance and Punctuality cannot exceed 20 points."
                )
            if record.work_quality > 30:
                raise ValidationError(
                    "Work Quality and Installation Accuracy cannot exceed 30 points."
                )
            if record.customer_interaction > 20:
                raise ValidationError("Customer Interaction cannot exceed 20 points.")
            if record.proactivity_initiative > 10:
                raise ValidationError(
                    "Proactivity and Initiative cannot exceed 10 points."
                )
            if record.uniform_safety > 10:
                raise ValidationError(
                    "Adherence to Uniform and Safety Regulations cannot exceed 10 points."
                )
            if record.reporting > 10:
                raise ValidationError(
                    "Reporting Observations and Malfunctions cannot exceed 10 points."
                )

    @api.constrains("employee_id", "date", "branch_id")
    def _check_evaluation_frequency(self):
        for record in self:
            if not record.employee_id or not record.date:
                return

            previous_evaluation = self.search(
                [
                    ("employee_id", "=", record.employee_id.id),
                    ("branch_id", "=", record.branch_id.id),
                    ("id", "!=", record.id),
                    ("date", "!=", False),
                ],
                order="date desc",
                limit=1,
            )

            if previous_evaluation:
                min_allowed_date = previous_evaluation.date + timedelta(days=30)

                if record.date <= min_allowed_date:
                    raise ValidationError(
                        f"Evaluation for employee {record.employee_id.name} cannot be done before {min_allowed_date.strftime('%d %B %Y')}. "
                        f"The previous evaluation was done on {previous_evaluation.date.strftime('%d %B %Y')}."
                    )

    @api.model
    def create(self, vals):

        record = super().create(vals)
        record._check_evaluation_frequency()
        return record

    @api.onchange("branch_id")
    def _onchange_branch_id(self):
        """
        Clear employee when branch changes and reset domain
        """
        if self.branch_id:
            return {"domain": {"employee_id": [("company_id", "=", self.branch_id.id)]}}
        else:
            return {"domain": {"employee_id": []}}

    def write(self, vals):
        """Block editing after creation, only Admin can edit"""
        if any(not rec._origin.id is None for rec in self):
            if not self.env.user.has_group("base.group_system"):
                raise UserError(
                    _("You cannot edit this record. Please contact the administrator.")
                )
        return super().write(vals)

    def unlink(self):
        """Block deleting after creation, only Admin can delete"""
        if any(not rec._origin.id is None for rec in self):
            if not self.env.user.has_group("base.group_system"):
                raise UserError(
                    _(
                        "You cannot delete this record. Please contact the administrator."
                    )
                )
        return super().unlink()
