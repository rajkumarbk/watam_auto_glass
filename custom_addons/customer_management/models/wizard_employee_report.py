from odoo import models, fields, api
from datetime import datetime, date
from odoo.exceptions import UserError
import json


class EmployeeReportWizard(models.TransientModel):
    _name = "employee.report.wizard"
    _description = "Employee Report Wizard"

    branch_id = fields.Many2one("res.company", string="Branch", required=True)
    use_date_filter = fields.Boolean(string="Use Date Filter", default=True)
    date_from = fields.Date(string="From Date")
    date_to = fields.Date(string="To Date")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Set default date range to current month
        today = date.today()
        first_day = today.replace(day=1)
        res["date_from"] = first_day
        res["date_to"] = today
        res["use_date_filter"] = True
        # Set default branch to current company
        res["branch_id"] = self.env.company.id
        return res

    def _get_report_data(self):
        """Get report data that will be used in the template"""
        # Get all employees from the selected branch
        employees = self.env["hr.employee"].search(
            [("company_id", "=", self.branch_id.id)]
        )

        # Build domain based on filters
        domain = [("branch_id", "=", self.branch_id.id), ("status", "=", "done")]

        # Add date filter only if use_date_filter is True
        if self.use_date_filter:
            if self.date_from:
                domain.append(("date", ">=", self.date_from))
            if self.date_to:
                domain.append(("date", "<=", self.date_to))

        records = self.env["customer.record"].search(domain)

        # Define all possible glass positions
        glass_positions = [
            "BDL",
            "BDR",
            "FDL",
            "FDR",
            "FQL",
            "FQR",
            "FVL",
            "FVR",
            "LFW",
            "RDL",
            "RDR",
            "RQL",
            "RQR",
            "SWL",
            "SWR",
            "SQL",
            "SQR",
            "RWH",
            "RWL",
            "RWM",
            "RWR",
            "ROOF",
        ]

        # Prepare data for report
        employee_data = {}
        for employee in employees:
            employee_name = employee.name or "Unknown"
            employee_data[employee_name] = {}

            # Initialize all glass positions with 0
            for glass_pos in glass_positions:
                employee_data[employee_name][glass_pos] = 0

        # Count actual work done by each employee
        for record in records:
            if record.employee_id:
                employee_name = record.employee_id.name or "Unknown"
                glass_name = (record.glass_destination.name or "Unknown").upper()

                # Map to standard glass positions
                if (
                    employee_name in employee_data
                    and glass_name in employee_data[employee_name]
                ):
                    employee_data[employee_name][glass_name] += 1

        # Prepare date display for report
        if self.use_date_filter:
            date_from_str = (
                self.date_from.strftime("%Y-%m-%d") if self.date_from else "Beginning"
            )
            date_to_str = (
                self.date_to.strftime("%Y-%m-%d") if self.date_to else "Present"
            )
        else:
            date_from_str = "All Time"
            date_to_str = ""

        return {
            "employee_data": employee_data,
            "branch_name": self.branch_id.name,
            "date_from": date_from_str,
            "date_to": date_to_str,
            "company_name": self.env.company.name,
            "use_date_filter": self.use_date_filter,
        }

    def action_print_report(self):
        """Generate employee report based on filters"""
        # Get report data
        report_data = self._get_report_data()

        if not report_data["employee_data"]:
            raise UserError("No data found for the selected criteria.")

        # Pass data through context
        return self.env.ref("customer_management.action_report_employee").report_action(
            self, data=report_data
        )
