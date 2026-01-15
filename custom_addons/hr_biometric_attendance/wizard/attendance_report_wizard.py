from datetime import datetime, timedelta
from odoo import api, fields, models, _
from pytz import timezone, UTC


class AttendanceReportWizard(models.TransientModel):
    _name = "attendance.report.wizard"
    _description = "Attendance Report Wizard"

    start_date = fields.Date(
        string="Start Date",
        required=True,
        default=lambda self: fields.Date.today().replace(day=1),
    )
    end_date = fields.Date(
        string="End Date", required=True, default=lambda self: fields.Date.today()
    )
    employee_ids = fields.Many2many(
        "hr.employee",
        string="Employees",
        help="Select employees for the report. Leave empty for all employees.",
    )

    def get_attendance_data(self):
        """Generate attendance data for every date in range, including weekends"""
        # Fetch attendance records
        domain = [
            ("punching_time", ">=", self.start_date),
            (
                "punching_time",
                "<=",
                self.end_date + timedelta(days=1) - timedelta(seconds=1),
            ),
        ]
        if self.employee_ids:
            domain.append(("employee_id", "in", self.employee_ids.ids))

        attendance_records = self.env["zk.machine.attendance"].search(
            domain, order="punching_time"
        )

        utc = UTC
        ksa_tz = timezone("Asia/Riyadh")

        # Organize punches by date and employee
        data_by_day = {}
        for record in attendance_records:
            utc_time = record.punching_time
            if utc_time.tzinfo is None:
                utc_time = utc.localize(utc_time)
            ksa_time = utc_time.astimezone(ksa_tz)
            date_str = ksa_time.date().strftime("%Y-%m-%d")
            employee_name = record.employee_id.name

            if date_str not in data_by_day:
                data_by_day[date_str] = {}

            if employee_name not in data_by_day[date_str]:
                data_by_day[date_str][employee_name] = {
                    "check_in": None,
                    "check_out": None,
                    "check_in_dt": None,
                    "check_out_dt": None,
                    "other_punches": [],
                    "device_id": record.device_id_num,
                    "address": record.address_id.name if record.address_id else "",
                }

            punch_time = ksa_time.strftime("%H:%M:%S")
            if record.punch_type == "0":
                data_by_day[date_str][employee_name]["check_in"] = punch_time
                data_by_day[date_str][employee_name]["check_in_dt"] = ksa_time
            elif record.punch_type == "1":
                data_by_day[date_str][employee_name]["check_out"] = punch_time
                data_by_day[date_str][employee_name]["check_out_dt"] = ksa_time
            else:
                punch_type_mapping = {
                    "2": "Break Out",
                    "3": "Break In",
                    "4": "Overtime In",
                    "5": "Overtime Out",
                    "255": "Duplicate",
                }
                punch_label = punch_type_mapping.get(
                    record.punch_type, record.punch_type
                )
                data_by_day[date_str][employee_name]["other_punches"].append(
                    f"{punch_time} ({punch_label})"
                )

        # Build full report: one row per employee per date
        report_data = []
        current_date = self.start_date
        while current_date <= self.end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            day_name = current_date.strftime("%a")  # Mon, Tue, ..., Fri, Sat, Sun

            # Determine employees to show
            if self.employee_ids:
                employees = self.employee_ids
            else:
                # All employees who have at least one record in the period
                all_names = set()
                for emp_dict in data_by_day.values():
                    all_names.update(emp_dict.keys())
                employees = (
                    self.env["hr.employee"].search([("name", "in", list(all_names))])
                    if all_names
                    else self.env["hr.employee"].search([])
                )

            employees_on_date = data_by_day.get(date_str, {})

            for employee in employees:
                emp_name = employee.name
                data = employees_on_date.get(
                    emp_name,
                    {
                        "check_in": None,
                        "check_out": None,
                        "check_in_dt": None,
                        "check_out_dt": None,
                        "device_id": "",
                        "address": "",
                        "other_punches": [],
                    },
                )

                check_in = data["check_in"] or "-"
                check_out = data["check_out"] or "-"

                total_hours = "-"
                if (
                    data["check_in"]
                    and data["check_out"]
                    and data["check_in_dt"]
                    and data["check_out_dt"]
                ):
                    if data["check_out_dt"] > data["check_in_dt"]:
                        duration = data["check_out_dt"] - data["check_in_dt"]
                        secs = int(duration.total_seconds())
                        h = secs // 3600
                        m = (secs % 3600) // 60
                        s = secs % 60
                        total_hours = f"{h:02d}:{m:02d}:{s:02d}"

                # Decide if absent
                absent = ""
                is_weekend = day_name in ["Fri", "Sat"]
                has_attendance = data["check_in"] or data["check_out"]
                complete_attendance = data["check_in"] and data["check_out"]

                if not is_weekend and not complete_attendance:
                    absent = "Yes"  # Only working days with incomplete/no attendance are absent

                report_data.append(
                    {
                        "date": date_str,
                        "day": day_name,
                        "employee": emp_name,
                        "device_id": data.get("device_id", ""),
                        "check_in": check_in,
                        "check_out": check_out,
                        "total_hours": total_hours,
                        "absent": absent,
                        "punch_type": (
                            ", ".join(data["other_punches"])
                            if data["other_punches"]
                            else "Normal"
                        ),
                        "address": data.get("address", ""),
                    }
                )

            current_date += timedelta(days=1)

        report_data.sort(key=lambda x: (x["date"], x["employee"]))
        return report_data

    def get_summary_data(self):
        """Summary with absent count excluding Fridays and Saturdays"""
        attendance_data = self.get_attendance_data()

        # All days in period (for counting possible working days)
        working_days = []
        current = self.start_date
        while current <= self.end_date:
            if current.strftime("%a") not in ["Fri", "Sat"]:
                working_days.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)

        # Employees
        if self.employee_ids:
            employees = self.employee_ids
        else:
            employees = self.env["hr.employee"].search([])

        summary = {}
        for emp in employees:
            summary[emp.name] = {
                "employee": emp.name,
                "worked_days": 0,
                "total_hours_seconds": 0,
                "absent_count": 0,
            }

        # Process records
        for rec in attendance_data:
            emp = rec["employee"]
            if emp not in summary:
                continue

            day_name = rec["day"]
            is_weekend = day_name in ["Fri", "Sat"]

            if not is_weekend and rec["absent"] == "Yes":
                summary[emp]["absent_count"] += 1

            if rec["total_hours"] != "-" and not is_weekend:
                try:
                    h, m, s = map(int, rec["total_hours"].split(":"))
                    summary[emp]["total_hours_seconds"] += h * 3600 + m * 60 + s
                    summary[emp]["worked_days"] += 1
                except:
                    pass

        # Format summary
        result = []
        for data in summary.values():
            secs = data["total_hours_seconds"]
            h = secs // 3600
            m = (secs % 3600) // 60
            result.append(
                {
                    "employee": data["employee"],
                    "worked_days": data["worked_days"],
                    "worked_hours": f"{h:02d}:{m:02d}",
                    "absent_count": data["absent_count"],
                }
            )

        result.sort(key=lambda x: x["employee"])
        return result

    def print_report(self):
        return self.env.ref(
            "hr_biometric_attendance.action_report_attendance"
        ).report_action(self)
