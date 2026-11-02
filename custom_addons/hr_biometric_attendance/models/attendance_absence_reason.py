from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AttendanceAbsenceReason(models.Model):
    _name = "attendance.absence.reason"
    _description = "Attendance Absence Reason"

    employee_id = fields.Many2one("hr.employee", string="Employee",
                                  help="Empty = applies to all employees")
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    reason = fields.Char(required=True)

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for rec in self:
            if rec.date_to < rec.date_from:
                raise ValidationError("Date To must be after Date From.")

    @api.constrains("employee_id", "date_from", "date_to")
    def _check_overlap(self):
        for rec in self:
            domain = [
                ("id", "!=", rec.id),
                ("date_from", "<=", rec.date_to),
                ("date_to", ">=", rec.date_from),
                "|", ("employee_id", "=", rec.employee_id.id),
                     ("employee_id", "=", False),
            ]
            if not rec.employee_id:
                domain = [
                    ("id", "!=", rec.id),
                    ("date_from", "<=", rec.date_to),
                    ("date_to", ">=", rec.date_from),
                ]
            if self.search_count(domain):
                raise ValidationError("Overlapping absence reason exists.")

    @api.model
    def get_reason(self, employee, date):
        domain = [("date_from", "<=", date), ("date_to", ">=", date)]
        rec = self.search(domain + [("employee_id", "=", employee.id)], limit=1)
        if not rec:
            rec = self.search(domain + [("employee_id", "=", False)], limit=1)
        return rec.reason if rec else False