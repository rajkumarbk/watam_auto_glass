from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from odoo.exceptions import ValidationError, UserError
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
        string="Search Record: ",
        domain=[("status", "=", "done")],
    )
    invoice_number = fields.Char(
        related="vehicle_record_id.invoice_number",
        store=True,
        string="Invoice number",
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
    service_complexity = fields.Selection(
        [
            ("easy", "Easy"),
            ("medium", "Medium"),
            ("complex", "Complex"),
        ],
        string="Service Complexity",
    )
    service_type = fields.Selection(
        [("service", "Service"), ("glass_sale", "Glass Installation")],
        string="Service Type",
    )
    service_option = fields.Many2one("service.option", string="Service Option")
    glass_option = fields.Selection(
        [("our_glass", "Sale & installation"), ("retailer_glass", "Installation only")],
        string="Glass Installation Options",
    )
    retailer_type = fields.Selection(
        [("oem", "OEM"), ("aftermarket", "Aftermarket")], string="Installation Type"
    )
    glass_destination = fields.Many2one("vehicle.glass", string="Glass Destination")
    submitted = fields.Boolean(string="Submitted", default=False, readonly=True)

    # Security methods
    def write(self, vals):
        """Prevent editing records after submission for non-admin users"""
        for record in self:
            if record.submitted and not self.env.user.has_group("base.group_system"):
                raise UserError(
                    _("You cannot edit a submitted record. Please contact the administrator.")
                )
        return super().write(vals)

    def unlink(self):
        """Block deleting submitted records, except for Admins"""
        for record in self:
            if record.submitted and not self.env.user.has_group("base.group_system"):
                raise UserError(
                    _("You cannot delete a submitted record. Please contact the administrator.")
                )
        return super().unlink()

    def action_submit(self):
        """Mark the record as submitted (makes it non-editable)"""
        self.write({'submitted': True})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Record has been submitted and is now read-only.'),
                'type': 'success',
                'sticky': False,
                "target": "current",
            }
        }

    # Onchange methods
    @api.onchange("vehicle_record_id")
    def _onchange_vehicle_record(self):
        """Update fields when vehicle record is selected"""
        if self.vehicle_record_id:
            cr = self.vehicle_record_id

            update_fields = {
                "vehicle_brand": cr.vehicle_brand.id,
                "vehicle_model": cr.vehicle_model.id,
                "manufactured_year_id": cr.manufactured_year_id.id,
                "employee_id": cr.employee_id.id,
                "name": cr.name,
                "phone": cr.phone,
                "glass_destination": cr.glass_destination.id,
                "workplace": cr.workplace,
                "service_complexity": cr.service_complexity,
                "service_type": cr.service_type,
                "service_option": cr.service_option,
                "glass_option": cr.glass_option,
                "retailer_type": cr.retailer_type,
            }
            self.update(update_fields)

    # Computed methods
    @api.depends("vehicle_brand", "vehicle_model", "manufactured_year_id")
    def _compute_vehicle_display(self):
        """Compute vehicle display info by concatenating related fields"""
        for rec in self:
            parts = [
                rec.vehicle_brand.name if rec.vehicle_brand else "",
                rec.vehicle_model.name if rec.vehicle_model else "",
                rec.manufactured_year_id.name if rec.manufactured_year_id else "",
                rec.vehicle_brand.name if rec.vehicle_brand else "",
                rec.vehicle_model.name if rec.vehicle_model else "",
                rec.manufactured_year_id.name if rec.manufactured_year_id else "",
            ]
            rec.vehicle_display = " ".join(filter(None, parts))