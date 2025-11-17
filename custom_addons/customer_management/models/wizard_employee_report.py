from odoo import models, fields, api
from datetime import datetime, date
from odoo.exceptions import UserError
import json


class EmployeeReportWizard(models.TransientModel):
    _name = "employee.report.wizard"
    _description = "Employee Report Wizard"

    branch_id = fields.Many2one("res.company", string="Branch", required=True)
    employee_ids = fields.Many2many(
        "hr.employee", string="Employees", domain="[('company_id', '=', branch_id)]"
    )
    glass_destination_ids = fields.Many2many(
        "vehicle.glass",
        string="Glass Positions",
        required=False,  # Changed to not required
    )
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

        # NO default selections - user will select manually

        return res

    @api.onchange("branch_id")
    def _onchange_branch_id(self):
        """Update domain when branch changes"""
        if self.branch_id:
            return {
                "domain": {
                    "employee_ids": [("company_id", "=", self.branch_id.id)],
                    "glass_destination_ids": [],  # Glass positions are global, no domain needed
                }
            }
        else:
            return {"domain": {"employee_ids": [], "glass_destination_ids": []}}

    def _get_report_data(self):
        """Get report data that will be used in the template"""
        # Build domain based on filters
        domain = [("branch_id", "=", self.branch_id.id), ("status", "=", "done")]

        # Add employee filter if selected
        if self.employee_ids:
            domain.append(("employee_id", "in", self.employee_ids.ids))

        # Add glass destination filter only if selected
        if self.glass_destination_ids:
            domain.append(("glass_destination", "in", self.glass_destination_ids.ids))

        # Add date filter only if use_date_filter is True
        if self.use_date_filter:
            if self.date_from:
                domain.append(("date", ">=", self.date_from))
            if self.date_to:
                domain.append(("date", "<=", self.date_to))

        records = self.env["customer.record"].search(domain)

        # Get all possible glass positions or only selected ones
        if self.glass_destination_ids:
            # Use selected glass positions
            selected_glass_positions = []
            for glass in self.glass_destination_ids:
                glass_name = (glass.name or "").upper().strip()
                if glass_name:
                    selected_glass_positions.append(glass_name)
        else:
            # Use all glass positions from the system
            all_glass_positions = self.env["vehicle.glass"].search([])
            selected_glass_positions = []
            for glass in all_glass_positions:
                glass_name = (glass.name or "").upper().strip()
                if glass_name:
                    selected_glass_positions.append(glass_name)

        # Prepare data for report - only for selected employees
        employee_data = {}

        # Get selected employees or all employees from branch if none selected
        if self.employee_ids:
            employees = self.employee_ids
        else:
            employees = self.env["hr.employee"].search(
                [("company_id", "=", self.branch_id.id)]
            )

        # Initialize employee data structure
        for employee in employees:
            employee_name = employee.name or "Unknown"
            employee_data[employee_name] = {}
            for glass_pos in selected_glass_positions:
                employee_data[employee_name][glass_pos] = 0

        # Count actual work done by each employee
        for record in records:
            if record.employee_id and record.glass_destination:
                employee_name = record.employee_id.name or "Unknown"
                glass_name = (
                    (record.glass_destination.name or "Unknown").upper().strip()
                )

                # Only count if this employee is in our selected list and glass position is in our list
                if (
                    employee_name in employee_data
                    and glass_name in employee_data[employee_name]
                ):
                    employee_data[employee_name][glass_name] += 1

        # Filter out positions that have zero values across all employees (optional)
        active_glass_positions = []
        for glass_pos in selected_glass_positions:
            column_total = sum(
                employee_data[emp].get(glass_pos, 0) for emp in employee_data
            )
            if column_total > 0:  # Only include positions with data
                active_glass_positions.append(glass_pos)

        # If you want to show all selected positions even if zero, use this instead:
        # active_glass_positions = selected_glass_positions

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

        # Prepare selected employee names for display
        if self.employee_ids:
            selected_employee_names = ", ".join([emp.name for emp in self.employee_ids])
        else:
            selected_employee_names = "All Employees"

        # Prepare selected glass names for display
        if self.glass_destination_ids:
            selected_glass_names = ", ".join(
                [glass.name for glass in self.glass_destination_ids]
            )
        else:
            selected_glass_names = "All Glass Positions"

        return {
            "employee_data": employee_data,
            "branch_name": self.branch_id.name,
            "date_from": date_from_str,
            "date_to": date_to_str,
            "company_name": self.env.company.name,
            "use_date_filter": self.use_date_filter,
            "selected_employee": selected_employee_names,
            "selected_glass": selected_glass_names,  # Add this for display in report if needed
            "active_glass_positions": active_glass_positions,
        }

    def action_print_report(self):
        """Generate employee report based on filters"""
        # Validate that at least one employee is available in the branch
        employees_in_branch = self.env["hr.employee"].search(
            [("company_id", "=", self.branch_id.id)]
        )
        if not employees_in_branch:
            raise UserError("No employees found in the selected branch.")

        # Get report data
        report_data = self._get_report_data()

        if not report_data["employee_data"]:
            raise UserError("No data found for the selected criteria.")

        # Pass data through context
        return self.env.ref("customer_management.action_report_employee").report_action(
            self, data=report_data
        )
