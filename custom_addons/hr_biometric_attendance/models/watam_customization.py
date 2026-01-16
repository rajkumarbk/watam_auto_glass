from odoo import models, api, _
import logging

_logger = logging.getLogger(__name__)


class DailyAttendanceInherit(models.Model):
    _inherit = "daily.attendance"

    def print_attendance_report(self):
        """Open the attendance report wizard"""
        # Get employee IDs from current records if any
        employee_ids = self.mapped("employee_id").ids if self else []

        try:
            # The action is defined in hr_biometric_attendance module
            action = self.env.ref(
                "hr_biometric_attendance.action_attendance_report_wizard"
            )
            action = action.read()[0]

            # Set context with employee IDs if any records are selected
            if employee_ids:
                action["context"] = {
                    "default_employee_ids": [(6, 0, employee_ids)],
                    "default_start_date": False,
                    "default_end_date": False,
                }

            return action

        except ValueError as e:
            _logger.error(f"Action not found: {e}")
            # Fallback: Create dynamic action
            return {
                "type": "ir.actions.act_window",
                "name": "Attendance Report",
                "res_model": "attendance.report.wizard",
                "view_mode": "form",
                "target": "new",
                "context": {
                    "default_employee_ids": (
                        [(6, 0, employee_ids)] if employee_ids else False
                    ),
                },
            }
