from datetime import timedelta
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Inherited res.config.settings to add new fields"""

    _inherit = "res.config.settings"

    schedule_attendance_downloads = fields.Boolean(
        string="Schedule Downloads",
        config_parameter="hr_biometric_attendance.schedule_downloads",
        default=False,
        help="If Enabled we can " "schedule attendance " "downloading from " "device",
    )
    schedule_time_interval = fields.Integer(
        string="Schedule Time Interval",
        config_parameter="hr_biometric_attendance.schedule_time_interval",
        default=1,
        help="We can set Time interval " "for the Scheduling",
    )
    schedule_time_period = fields.Selection(
        selection=[("hours", "Hours"), ("days", "Days")],
        string="Schedule Time Period",
        config_parameter="hr_biometric_attendance.schedule_time_period",
        default="days",
        help="We can set Time Period for the Scheduling",
    )

    def set_values(self):
        """Super the function to set  the values from settings to the
        cron.job"""
        super().set_values()
        if self.schedule_attendance_downloads:
            self.env["ir.cron"].search(
                [("name", "=", "Schedule Attendance Downloading")]
            ).write(
                {
                    "active": True,
                    "interval_type": self.schedule_time_period,
                    "interval_number": self.schedule_time_interval,
                    "nextcall": (
                        fields.datetime.now()
                        + timedelta(hours=self.schedule_time_interval)
                        if self.schedule_time_period == "hours"
                        else fields.datetime.now()
                        + timedelta(days=self.schedule_time_interval)
                    ),
                }
            )
        else:
            self.env["ir.cron"].search(
                [("name", "=", "Schedule Attendance Downloading")]
            ).write({"active": False})
