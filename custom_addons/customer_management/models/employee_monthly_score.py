from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
import calendar


class EmployeeMonthlyScore(models.Model):
    _name = "employee.monthly.score"
    _description = "Employee of the Month Score"
    _order = "full_final_score desc"
    _rec_name = "employee_id"

    month = fields.Date(
        string="Month", required=True, help="Any date within target month"
    )
    branch_id = fields.Many2one(
        "res.company",
        string="Branch",
        required=True,
        default=lambda self: self.env.company,
    )
    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
        required=True,
        domain="[('company_id', '=', branch_id)]",
    )

    # Manual input
    google_review = fields.Integer(string="Google Review Count", default=0)

    # Per-employee raw counts
    complex_done = fields.Integer(compute="_compute_work_counts", store=True)
    med_done = fields.Integer(compute="_compute_work_counts", store=True)
    easy_done = fields.Integer(compute="_compute_work_counts", store=True)
    sec_tech_count = fields.Integer(compute="_compute_sec_tech", store=True)
    supervisor_score = fields.Float(compute="_compute_supervisor_score", store=True)

    # Branch-wide totals (same across all emp rows of same branch/month)
    total_emp_branch = fields.Integer(compute="_compute_branch_totals", store=True)
    total_complex_branch = fields.Integer(compute="_compute_branch_totals", store=True)
    total_med_branch = fields.Integer(compute="_compute_branch_totals", store=True)
    total_easy_branch = fields.Integer(compute="_compute_branch_totals", store=True)

    # Percentages
    avg_complex = fields.Float(compute="_compute_avg", store=True)
    avg_med = fields.Float(compute="_compute_avg", store=True)
    avg_easy = fields.Float(compute="_compute_avg", store=True)

    # Final weighted scores
    final_complex_score = fields.Float(compute="_compute_final_scores", store=True)
    final_med_score = fields.Float(compute="_compute_final_scores", store=True)
    final_easy_score = fields.Float(compute="_compute_final_scores", store=True)
    final_google_score = fields.Float(compute="_compute_final_scores", store=True)
    final_sec_tech_score = fields.Float(compute="_compute_final_scores", store=True)
    final_supervisor_score = fields.Float(compute="_compute_final_scores", store=True)
    full_final_score = fields.Float(compute="_compute_final_scores", store=True)

    _sql_constraints = [
        (
            "uniq_emp_branch_month",
            "unique(employee_id, branch_id, month)",
            "Score record already exists for this employee/branch/month.",
        )
    ]

    rank = fields.Integer(compute="_compute_rank", store=True)

    @api.depends("full_final_score", "month")
    def _compute_rank(self):
        months = self.mapped("month")
        all_recs = self.search([("month", "in", months)]) if months else self
        all_recs |= self
        groups = {}
        for rec in all_recs:
            groups.setdefault(rec.month, []).append(rec)
        for month, recs in groups.items():
            ordered = sorted(recs, key=lambda r: r.full_final_score, reverse=True)
            for i, r in enumerate(ordered, start=1):
                r.rank = i

    # ---------- Helpers ----------
    def _get_month_range(self):
        self.ensure_one()
        d = self.month
        date_from = d.replace(day=1)
        last_day = calendar.monthrange(d.year, d.month)[1]
        date_to = d.replace(day=last_day)
        return date_from, date_to

    # ---------- Computes ----------
    @api.depends("employee_id", "branch_id", "month")
    def _compute_work_counts(self):
        for rec in self:
            if not (rec.employee_id and rec.branch_id and rec.month):
                rec.complex_done = rec.med_done = rec.easy_done = 0
                continue
            date_from, date_to = rec._get_month_range()
            base_domain = [
                ("employee_id", "=", rec.employee_id.id),
                ("branch_id", "=", rec.branch_id.id),
                ("status", "=", "done"),
                ("date", ">=", date_from),
                ("date", "<=", date_to),
            ]
            CR = self.env["customer.record"]
            rec.complex_done = CR.search_count(
                base_domain + [("service_complexity", "=", "complex")]
            )
            rec.med_done = CR.search_count(
                base_domain + [("service_complexity", "=", "medium")]
            )
            rec.easy_done = CR.search_count(
                base_domain + [("service_complexity", "=", "easy")]
            )

    @api.depends("employee_id", "branch_id", "month")
    def _compute_sec_tech(self):
        for rec in self:
            if not (rec.employee_id and rec.branch_id and rec.month):
                rec.sec_tech_count = 0
                continue
            date_from, date_to = rec._get_month_range()
            rec.sec_tech_count = self.env["customer.record"].search_count(
                [
                    ("assistant_staff", "=", rec.employee_id.id),
                    ("branch_id", "=", rec.branch_id.id),
                    ("status", "=", "done"),
                    ("date", ">=", date_from),
                    ("date", "<=", date_to),
                ]
            )

    @api.depends("employee_id", "branch_id", "month")
    def _compute_supervisor_score(self):
        for rec in self:
            if not (rec.employee_id and rec.branch_id and rec.month):
                rec.supervisor_score = 0.0
                continue
            date_from, date_to = rec._get_month_range()
            evaluation = self.env["evaluation.criteria"].search(
                [
                    ("employee_id", "=", rec.employee_id.id),
                    ("branch_id", "=", rec.branch_id.id),
                    ("date", ">=", date_from),
                    ("date", "<=", date_to),
                ],
                order="date desc",
                limit=1,
            )
            rec.supervisor_score = evaluation.total_score if evaluation else 0.0

    @api.depends("branch_id", "month")
    def _compute_branch_totals(self):
        for rec in self:
            if not (rec.branch_id and rec.month):
                rec.total_emp_branch = rec.total_complex_branch = (
                    rec.total_med_branch
                ) = rec.total_easy_branch = 0
                continue
            date_from, date_to = rec._get_month_range()
            CR = self.env["customer.record"]
            base_domain = [
                ("branch_id", "=", rec.branch_id.id),
                ("status", "=", "done"),
                ("date", ">=", date_from),
                ("date", "<=", date_to),
            ]
            rec.total_complex_branch = CR.search_count(
                base_domain + [("service_complexity", "=", "complex")]
            )
            rec.total_med_branch = CR.search_count(
                base_domain + [("service_complexity", "=", "medium")]
            )
            rec.total_easy_branch = CR.search_count(
                base_domain + [("service_complexity", "=", "easy")]
            )
            emp_ids = CR.search(base_domain).mapped("employee_id")
            rec.total_emp_branch = len(emp_ids)

    @api.depends(
        "total_emp_branch",
        "total_complex_branch",
        "total_med_branch",
        "total_easy_branch",
    )
    def _compute_avg(self):
        for rec in self:
            n = rec.total_emp_branch
            rec.avg_complex = rec.total_complex_branch / n if n else 0.0
            rec.avg_med = rec.total_med_branch / n if n else 0.0
            rec.avg_easy = rec.total_easy_branch / n if n else 0.0

    @api.depends(
        "complex_done",
        "med_done",
        "easy_done",
        "avg_complex",
        "avg_med",
        "avg_easy",
        "google_review",
        "sec_tech_count",
        "supervisor_score",
        "total_complex_branch",
        "total_med_branch",
        "total_easy_branch",
    )
    def _compute_final_scores(self):
        for rec in self:
            total_done = rec.easy_done + rec.med_done + rec.complex_done
            total_branch = (
                rec.total_easy_branch + rec.total_med_branch + rec.total_complex_branch
            )
            rec.final_complex_score = min(
                (rec.complex_done / rec.avg_complex) * 2.0
                if rec.avg_complex else 0.0,
                2.0
            )

            rec.final_med_score = min(
                (rec.med_done / rec.avg_med) * 1.5
                if rec.avg_med else 0.0,
                1.5
            )

            rec.final_easy_score = min(
                (rec.easy_done / rec.avg_easy) * 1.5
                if rec.avg_easy else 0.0,
                1.5
            )
            rec.final_google_score = (
                (rec.google_review / total_done) * 3.0 if rec.google_review else 0.0
            )
            rec.final_sec_tech_score = (
                (rec.sec_tech_count / total_branch) * 0.5 if rec.sec_tech_count else 0.0
            )
            rec.final_supervisor_score = (rec.supervisor_score / 100) * 1.5
            rec.full_final_score = (
                rec.final_complex_score
                + rec.final_med_score
                + rec.final_easy_score
                + rec.final_google_score
                + rec.final_sec_tech_score
                + rec.final_supervisor_score
            )

    # ---------- Generation ----------
    @api.model
    def generate_monthly_scores(self, month_date, branch_id=False):
        """Create score records for every employee with a completed
        work order in the given month/branch. Skips existing records."""
        month_date = fields.Date.to_date(month_date)
        date_from = month_date.replace(day=1)
        last_day = calendar.monthrange(month_date.year, month_date.month)[1]
        date_to = month_date.replace(day=last_day)

        branches = (
            self.env["res.company"].browse(branch_id)
            if branch_id
            else self.env["res.company"].search([])
        )
        created = self.env["employee.monthly.score"]
        CR = self.env["customer.record"]

        for branch in branches:
            emp_ids = CR.search(
                [
                    ("branch_id", "=", branch.id),
                    ("status", "=", "done"),
                    ("date", ">=", date_from),
                    ("date", "<=", date_to),
                ]
            ).mapped("employee_id")

            for emp in emp_ids:
                exists = self.search(
                    [
                        ("employee_id", "=", emp.id),
                        ("branch_id", "=", branch.id),
                        ("month", "=", date_from),
                    ],
                    limit=1,
                )
                if not exists:
                    created |= self.create(
                        {
                            "employee_id": emp.id,
                            "branch_id": branch.id,
                            "month": date_from,
                        }
                    )
        return created
