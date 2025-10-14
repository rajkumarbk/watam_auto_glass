from odoo import models, fields, api
from odoo.exceptions import ValidationError


class EvaluationCriteria(models.Model):
    _name = "evaluation.criteria"
    _description = "Evaluation Criteria"

    branch_id = fields.Many2one("res.company", string="Branch", required=True)
    employee_id = fields.Many2one("hr.employee", string="Employee", required=True)

    # Evaluation fields
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
