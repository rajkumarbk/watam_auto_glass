from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime
import pytz
import re
import logging

_logger = logging.getLogger(__name__)


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
        store=True,
        copy=True,  # Ensure it's copied when duplicating records
    )
    new_branch_id = fields.Many2one(
        "res.company",
        string="Current branch",
        default=lambda self: self.env.company,
    )
    previous_date = fields.Date(
        string="Previous Service Date",
        store=True,
        readonly=True,
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

    @api.model
    def create(self, vals):
        """Override create to ensure branch_id and previous_date are properly saved"""
        # Log for debugging
        if 'branch_id' in vals:
            _logger.info(f"Creating record with branch_id: {vals.get('branch_id')}")
        if 'previous_date' in vals:
            _logger.info(f"Creating record with previous_date: {vals.get('previous_date')}")
        return super(ProblemSolution, self).create(vals)

    # Security methods
    def write(self, vals):
        """Prevent editing records after submission for non-admin users"""
        # Log for debugging
        if 'branch_id' in vals:
            _logger.info(f"Writing branch_id: {vals.get('branch_id')} for record {self.id}")
        if 'previous_date' in vals:
            _logger.info(f"Writing previous_date: {vals.get('previous_date')} for record {self.id}")
        
        for record in self:
            if record.submitted and not self.env.user.has_group("base.group_system"):
                # Allow only status changes after submission
                if set(vals.keys()) - {'status', 'submitted'}:
                    raise UserError(
                        _(
                            "You cannot edit a submitted record. Please contact the administrator."
                        )
                    )
        return super(ProblemSolution, self).write(vals)

    def unlink(self):
        """Block deleting submitted records, except for Admins"""
        for record in self:
            if record.submitted and not self.env.user.has_group("base.group_system"):
                raise UserError(
                    _(
                        "You cannot delete a submitted record. Please contact the administrator."
                    )
                )
        return super(ProblemSolution, self).unlink()

    def action_submit(self):
        """Mark the record as submitted (makes it non-editable)"""
        for record in self:
            # Get current branch_id and previous_date before any updates
            current_branch = record.branch_id.id if record.branch_id else False
            current_previous_date = record.previous_date if record.previous_date else False
            
            # Explicitly preserve branch_id, previous_date and other important fields
            vals = {
                "submitted": True,
            }
            
            # Force include branch_id in the write operation
            if current_branch:
                vals['branch_id'] = current_branch
            
            # Force include previous_date in the write operation
            if current_previous_date:
                vals['previous_date'] = current_previous_date
            
            _logger.info(f"Submitting record {record.id} with branch_id: {current_branch}, previous_date: {current_previous_date}")
            record.write(vals)
            
            # Verify it was saved
            record.invalidate_cache(['branch_id', 'previous_date'])
            _logger.info(f"After submit, branch_id is: {record.branch_id.id if record.branch_id else 'False'}, previous_date is: {record.previous_date or 'False'}")
        
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "list,form",
            "target": "current",
        }

    @api.model
    def name_search(self, name, args=None, operator="ilike", limit=100):
        """Search by vehicle_number, invoice_number, or phone in problem.solution"""
        args = args or []
        domain = args + [
            "|",
            "|",
            ("vehicle_number", operator, name),
            ("invoice_number", operator, name),
            ("phone", operator, name),
        ]
        # Corrected: Search in current model (problem.solution) not customer.record
        records = self.search(domain, limit=limit)
        return records.name_get()

    @api.onchange("vehicle_record_id")
    def _onchange_vehicle_record(self):
        """Update fields when a vehicle record is selected"""
        if self.vehicle_record_id:
            cr = self.vehicle_record_id
            
            # Log the branch_id and date being loaded
            _logger.info(f"Loading branch_id from vehicle_record: {cr.branch_id.id if cr.branch_id else 'None'}")
            _logger.info(f"Loading date from vehicle_record: {cr.date or 'None'}")
            
            update_fields = {
                "vehicle_brand": cr.vehicle_brand.id if cr.vehicle_brand else False,
                "vehicle_model": cr.vehicle_model.id if cr.vehicle_model else False,
                "manufactured_year_id": cr.manufactured_year_id.id if cr.manufactured_year_id else False,
                "vehicle_display": cr.vehicle_display,
                "photo": cr.photo,
                "employee_id": cr.employee_id.id if cr.employee_id else False,
                "branch_id": cr.branch_id.id if cr.branch_id else False,
                "previous_date": cr.date if cr.date else False,  # Get the date from customer.record
                "assistant_staff": cr.assistant_staff.id if cr.assistant_staff else False,
                "name": cr.name,
                "phone": cr.phone,
                "glass_destination": cr.glass_destination.id if cr.glass_destination else False,
                "workplace": cr.workplace,
                "service_complexity": cr.service_complexity,
                "service_type": cr.service_type,
                "service_option": cr.service_option.id if cr.service_option else False,
                "glass_option": cr.glass_option,
                "retailer_type": cr.retailer_type,
                "invoice_number": cr.invoice_number,
            }
            self.update(update_fields)
        else:
            # Clear fields if no vehicle record is selected
            self.update({
                "vehicle_brand": False,
                "vehicle_model": False,
                "manufactured_year_id": False,
                "vehicle_display": False,
                "photo": False,
                "employee_id": False,
                "branch_id": False,
                "previous_date": False,
                "assistant_staff": False,
                "name": False,
                "phone": False,
                "glass_destination": False,
                "workplace": False,
                "service_complexity": False,
                "service_type": False,
                "service_option": False,
                "glass_option": False,
                "retailer_type": False,
                "invoice_number": False,
            })

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
        for record in self:
            # Preserve branch_id and previous_date when changing status
            vals = {"status": "started"}
            if record.branch_id:
                vals['branch_id'] = record.branch_id.id
            if record.previous_date:
                vals['previous_date'] = record.previous_date
            record.write(vals)
        
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "list,form",
            "domain": [("status", "=", "started")],
            "target": "current",
        }

    def action_set_done(self):
        """Set status to done, record end time, and return filtered view"""
        for record in self:
            # Preserve branch_id and previous_date when changing status
            vals = {"status": "done"}
            if record.branch_id:
                vals['branch_id'] = record.branch_id.id
            if record.previous_date:
                vals['previous_date'] = record.previous_date
            record.write(vals)
        
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "list,form",
            "domain": [("status", "=", "done")],
            "target": "current",
        }