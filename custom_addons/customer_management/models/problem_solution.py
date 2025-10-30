from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime
import pytz
import re


class ProblemSolution(models.Model):
    _name = "problem.solution"
    _description = "Problem and Solution"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc"
    _rec_name = "invoice_number"

    vehicle_record_id = fields.Many2one(
        "customer.record",
        string="Search Record: ",
        domain=[("status", "=", "done")],
    )
    vehicle_number = fields.Char(
        string="Car Registration Number",
        related="vehicle_record_id.vehicle_number",
        store=True,
    )
    invoice_number = fields.Char(
        store=True,
        string="Invoice number",
    )
    employee_id = fields.Many2one("hr.employee", string="Previous Employee")
    new_employee_id = fields.Many2one("hr.employee", string="Employee Name")
    assistant_staff = fields.Many2one("hr.employee", string="Secondary Technician")
    branch_id = fields.Many2one(
        "res.company",
        string="Previous branch",
    )
    new_branch_id = fields.Many2one(
        "res.company",
        string="Branch",
        default=lambda self: self.env.company,
    )
    name = fields.Char(
        string="Customer Name",
        store=True,
    )
    phone = fields.Char(
        string="Mobile Number",
        store=True,
    )
    vehicle_brand = fields.Many2one("vehicle.brand", string="Vehicle Brand")
    vehicle_model = fields.Many2one("vehicle.model", string="Vehicle Name")
    manufactured_year_id = fields.Many2one("manufactured.year", string="Vehicle Model")
    vehicle_display = fields.Char(
        string="Vehicle Info",
        compute="_compute_vehicle_display",
        store=True,
    )
    datetime = fields.Datetime(string="Date & Time", default=fields.Datetime.now)
    date = fields.Date(
        string="Previous Date",
        readonly=True,
    )
    new_date = fields.Date(
        string="Date",
        default=fields.Date.context_today,
        readonly=True,
    )
    photo = fields.Binary(string="Photo")
    notes = fields.Text(string="Notes")
    problem = fields.Many2one("what.problem", string="Type of complaint", required=True)
    solution = fields.Many2one("what.solution", string="Solution", required=True)
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

    # Security methods
    def write(self, vals):
        """Prevent editing records after submission for non-admin users"""
        for record in self:
            if record.submitted and not self.env.user.has_group("base.group_system"):
                raise UserError(
                    _(
                        "You cannot edit a submitted record. Please contact the administrator."
                    )
                )
        return super().write(vals)

    def unlink(self):
        """Block deleting submitted records, except for Admins"""
        for record in self:
            if record.submitted and not self.env.user.has_group("base.group_system"):
                raise UserError(
                    _(
                        "You cannot delete a submitted record. Please contact the administrator."
                    )
                )
        return super().unlink()

    def action_submit(self):
        """Mark the record as submitted (makes it non-editable)"""
        self.write({"submitted": True})
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "list,form",
            "target": "current",
        }

    @api.model
    def name_search(self, name, args=None, operator="ilike", limit=100):
        args = args or []
        domain = args + [
            "|",
            "|",
            ("vehicle_number", operator, name),
            ("invoice_number", operator, name),
            ("phone", operator, name),
        ]
        records = self.env["customer.record"].search(domain, limit=limit)
        return records.name_get()

    @api.onchange("vehicle_record_id")
    def _onchange_vehicle_record(self):
        if self.vehicle_record_id:
            cr = self.vehicle_record_id
            update_fields = {
                "vehicle_brand": cr.vehicle_brand.id,
                "vehicle_model": cr.vehicle_model.id,
                "manufactured_year_id": cr.manufactured_year_id.id,
                "vehicle_display": cr.vehicle_display,
                "photo": cr.photo,
                "employee_id": cr.employee_id.id,
                "branch_id": cr.branch_id.id,
                "date": cr.date,
                "assistant_staff": cr.assistant_staff.id,
                "name": cr.name,
                "phone": cr.phone,
                "glass_destination": cr.glass_destination.id,
                "workplace": cr.workplace,
                "service_complexity": cr.service_complexity,
                "service_type": cr.service_type,
                "service_option": cr.service_option,
                "glass_option": cr.glass_option,
                "retailer_type": cr.retailer_type,
                "invoice_number": cr.invoice_number,
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
            ]
            rec.vehicle_display = " ".join(filter(None, parts))

    # Action methods
    def action_set_started(self):
        """Set status to started and return filtered view"""
        self.write({"status": "started"})
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "list,form",
            "domain": [("status", "=", "started")],
            "target": "current",
        }

    def action_set_done(self):
        """Set status to done, record end time, and return filtered view"""
        self.write(
            {
                "status": "done",
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "list,form",
            "domain": [("status", "=", "done")],
            "target": "current",
        }
