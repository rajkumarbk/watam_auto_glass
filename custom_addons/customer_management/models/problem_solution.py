from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime
from time import time
import pytz
import re


class ProblemSolution(models.Model):
    _name = "problem.solution"
    _description = "Problem and Solution"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name asc"

    customer_record_id = fields.Many2one(
        "customer.record",
        string="Invoice Number",
        help="Select the related customer work order (invoice number)"
    )
    invoice_number = fields.Char(
        string="Invoice Num",
        related="customer_record_id.invoice_number",
        store=True,
        readonly=False  # if you want it editable, else keep True
    )
    employee_id = fields.Many2one("hr.employee", string="Employee")
    assistant_staff = fields.Many2one("hr.employee", string="Assistant Staff")
    branch_id = fields.Many2one(
        "res.company",
        string="Branch",
        default=lambda self: self.env.company,
    )
    name = fields.Char(string="Customer")
    phone = fields.Char(string="Phone", default="05")
    vehicle_brand = fields.Many2one("vehicle.brand", string="Vehicle Brand")
    vehicle_model = fields.Many2one("vehicle.model", string="Vehicle Model")
    manufactured_year_id = fields.Many2one(
        "manufactured.year", string="Manufactured Year"
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

    vehicle_number = fields.Char(string="Vehicle Number")
    
    datetime = fields.Datetime(
        string="Date & Time",
        default=fields.Datetime.now  # automatically sets current date & time
    )
    photo = fields.Binary(string="Photo")
    notes = fields.Text(string="Notes")


    def action_set_done(self):
        """Set status to done and record end_time"""
        for record in self:
            record.status = "done"
            record.end_time = self._get_ksa_time_float()

    problem = fields.Many2one(
        "what.problem", string="Problem", help="Problem of the vehicle"
    )

    solution = fields.Many2one("what.solution", string="Solution")

    workplace = fields.Selection(
        [
            ("inside", "Inside"),
            ("outside", "Outside"),
        ],
        string="Workplace",
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
    glass_destination = fields.Many2one("vehicle.glass", string="Glass Destination")

    @api.onchange("customer_record_id")
    def _onchange_customer_record(self):    
        for rec in self:
            if rec.customer_record_id:
                cr = rec.customer_record_id
                # rec.assistant_staff = cr.assistant_staff
                rec.vehicle_brand = cr.vehicle_brand
                rec.vehicle_model = cr.vehicle_model
                rec.manufactured_year_id = cr.manufactured_year_id
                rec.vehicle_number = cr.vehicle_number
                rec.employee_id = cr.employee_id
                # rec.name = cr.name
                # rec.phone = cr.phone
                # rec.glass_destination = cr.glass_destination
    
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
    # @api.constrains("phone")
    # def _check_phone(self):
    #     for record in self:
    #         if record.phone and not re.fullmatch(r"\d{10}", record.phone):
    #             raise ValidationError(_("Phone number must be exactly 10 digits."))
