from odoo import api, fields, models, _, exceptions
from odoo.exceptions import ValidationError
from datetime import datetime
import pytz
import re


class ClientRecord(models.Model):
    _name = "customer.record"
    _description = "Customer Records"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name asc"
    _rec_name = "invoice_number"

    employee_id = fields.Many2one("hr.employee", string="Employee Name")
    assistant_staff = fields.Many2one("hr.employee", string="Assistant Staff Name")
    branch_id = fields.Many2one(
        "res.company",
        string="Branch",
        default=lambda self: self.env.company,
    )
    name = fields.Char(string="Customer Name", required=True)
    phone = fields.Char(string="Contact Number", required=True)
    vehicle_brand = fields.Many2one(
        "vehicle.brand", string="Vehicle Brand", required=True
    )
    vehicle_model = fields.Many2one(
        "vehicle.model", string="Vehicle Model", required=True
    )
    manufactured_year_id = fields.Many2one(
        "manufactured.year", string="Manufactured Year", required=True
    )

    available_year_ids = fields.Many2many(
        "manufactured.year",
        string="Available Years",
        compute="_compute_available_years",
    )

    vehicle_display = fields.Char(
        string="Vehicle Info",
        compute="_compute_vehicle_display",
    )

    vehicle_number = fields.Char(string="Vehicle Number", required=True)
    date = fields.Date(
        string="Date",
        default=fields.Date.context_today,
        readonly=True,
    )
    photo = fields.Binary(string="Photo")
    notes = fields.Text(string="Notes")

    def _get_current_time_float(self):
        # Get current time in your timezone, e.g., Asia/Riyadh
        tz = pytz.timezone("Asia/Riyadh")
        now = datetime.now(tz)
        return now.hour + now.minute / 60.0  # convert to float

    start_time = fields.Float(
        string="Start Time", readonly=True, default=_get_current_time_float
    )
    end_time = fields.Float(string="End Time", readonly=True)

    def action_set_done(self):
        """Set status to done and record end_time"""
        for record in self:
            record.status = "done"
            record.end_time = self._get_current_time_float()

    workplace = fields.Selection(
        [
            ("inside", "Inside"),
            ("outside", "Outside"),
        ],
        string="Workplace",
        default = "inside",
        required=True,
    )

    status = fields.Selection(
        [
            ("not_started", "Not Started"),
            ("started", "Started"),
            ("done", "Finished"),
        ],
        string="Status",
        default="not_started",
        tracking=True,
    )

    glass_destination = fields.Many2one(
        "vehicle.glass", string="Glass Destination", required=True
    )
    invoice_number = fields.Char(string="Invoice Number", required=True)

    # Compute Methods

    @api.depends("vehicle_model")
    def _compute_available_years(self):
        for rec in self:
            rec.available_year_ids = rec.vehicle_model.manufactured_year_id

    @api.depends("vehicle_brand", "vehicle_model", "manufactured_year_id")
    def _compute_vehicle_display(self):
        for rec in self:
            rec.vehicle_display = " ".join(
                filter(
                    None,
                    [
                        rec.vehicle_brand.name,
                        rec.vehicle_model.name,
                        rec.manufactured_year_id.name,
                    ],
                )
            )

    # Button Actions

    def action_set_started(self):
        self.status = "started"

    def action_set_on_progress(self):
        """⚠️ Note: 'on_progress' is not in your selection.
        Either add it in `status` field or this will raise a ValueError."""
        self.status = "on_progress"

    # Constraints

    @api.constrains("phone")
    def _check_phone(self):
        for record in self:
            if record.phone and not re.fullmatch(r"\d{10}", record.phone):
                raise ValidationError(_("Phone number must be exactly 10 digits."))
