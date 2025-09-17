from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime
import pytz
import re


class ProblemSolution(models.Model):
    _name = "problem.solution"
    _description = "Problem and Solution"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name asc"

    # Helper method
    def _get_ksa_time_float(self):
        """Get current time in float format for KSA timezone"""
        tz = pytz.timezone("Asia/Riyadh")
        now = datetime.now(tz)
        return now.hour + now.minute / 60.0

    # Fields definition
    vehicle_record_id = fields.Many2one(
        "customer.record",
        string="Search Record",
        domain=[("status", "=", "done")],
    )
    invoice_number = fields.Char(
        related="vehicle_record_id.invoice_number",
        store=True,
        string="Inv No",
    )
    employee_id = fields.Many2one("hr.employee", string="Employee Name")
    assistant_staff = fields.Many2one("hr.employee", string="Secondary Technician")
    branch_id = fields.Many2one(
        "res.company",
        string="Branch Name",
        default=lambda self: self.env.company,
    )
    name = fields.Char(
        string="Customer Name",
        related="vehicle_record_id.name",
        store=True,
    )
    phone = fields.Char(
        string="Mobile Number",
        related="vehicle_record_id.phone",
        store=True,
    )
    vehicle_brand = fields.Many2one("vehicle.brand", string="Car Brand")
    vehicle_model = fields.Many2one("vehicle.model", string="Car Name")
    manufactured_year_id = fields.Many2one("manufactured.year", string="Car Model")
    vehicle_display = fields.Char(
        string="Vehicle Info",
        compute="_compute_vehicle_display",
        store=True,  
    )
    vehicle_number = fields.Char(
        string="Car Registration Number",
        related="vehicle_record_id.vehicle_number",
        store=True,
    )
    datetime = fields.Datetime(string="Date & Time", default=fields.Datetime.now)
    photo = fields.Binary(string="Photo")
    notes = fields.Text(string="Notes")
    problem = fields.Many2one("what.problem", string="Problem", required=True)
    solution = fields.Many2one("what.solution", string="Solution")
    workplace = fields.Selection(
        [
            ("inside", "Workshop"),
            ("outside", "External"),
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

    # Onchange methods
    @api.onchange("vehicle_record_id")
    def _onchange_vehicle_record(self):
        """Update fields when vehicle record is selected"""
        if self.vehicle_record_id:
            cr = self.vehicle_record_id
           
            update_fields = {
                'vehicle_brand': cr.vehicle_brand.id,
                'vehicle_model': cr.vehicle_model.id,
                'manufactured_year_id': cr.manufactured_year_id.id,
                'employee_id': cr.employee_id.id,
                'name': cr.name,
                'phone': cr.phone,
                'glass_destination': cr.glass_destination.id,
            }
            self.update(update_fields)

    # Computed methods
    @api.depends("vehicle_brand", "vehicle_model", "manufactured_year_id")
    def _compute_vehicle_display(self):
        """Compute vehicle display info by concatenating related fields"""
        for rec in self:
            parts = [
                rec.vehicle_brand.name,
                rec.vehicle_model.name,
                rec.manufactured_year_id.name,
            ]
            rec.vehicle_display = " ".join(filter(None, parts))

    # Button action methods
    def action_set_done(self):
        """Set status to done for all selected records"""
        self.write({'status': 'done'})  

    def action_set_started(self):
        """Set status to started for all selected records"""
        self.write({'status': 'started'})  