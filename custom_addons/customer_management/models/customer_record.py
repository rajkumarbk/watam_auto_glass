from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime
import pytz
import re


class ClientRecord(models.Model):
    _name = "customer.record"
    _description = "Customer Records"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc"
    _rec_name = "vehicle_number"

    
    
    # Fields definition
    employee_id = fields.Many2one("hr.employee", string="Employee Name")
    assistant_staff = fields.Many2one("hr.employee", string="Secondary Technician")
    branch_id = fields.Many2one(
        "res.company",
        string="Branch Name",
        default=lambda self: self.env.company,
    )
    name = fields.Char(string="Customer Name", required=True)
    phone = fields.Char(string="Mobile Number", required=True, size=10)
    vehicle_brand = fields.Many2one(
        "vehicle.brand", string="Vehicle Brand", required=True
    )
    vehicle_model = fields.Many2one(
        "vehicle.model", string="Vehicle Name", required=True
    )
    manufactured_year_id = fields.Many2one(
        "manufactured.year", string="Vehicle Model", required=True
    )
    vehicle_display = fields.Char(
        string="Vehicle Info",
        compute="_compute_vehicle_display",
        store=True,
    )
    vehicle_number = fields.Char(
        string="Vehicle Registration Number", size=10, required=True
    )
    date = fields.Date(
        string="Date",
        default=fields.Date.context_today,
        readonly=True,
    )
    photo = fields.Binary(string="Photo")
    notes = fields.Text(string="Notes")

    def _get_current_time_string(self):
        utc_now = datetime.now(pytz.UTC)
        local_tz = pytz.timezone("Asia/Riyadh")
        local_time = utc_now.astimezone(local_tz)
        return local_time.strftime("%I:%M %p")

    start_time = fields.Char(
        string="WO Start Time", readonly=True, default=_get_current_time_string)
    
    def _get_current_time_string(self):
        utc_now = datetime.now(pytz.UTC)
        local_tz = pytz.timezone('Asia/Riyadh')
        local_time = utc_now.astimezone(local_tz)
        return local_time.strftime('%I:%M %p')

    start_time = fields.Char(
        string="WO Start Time", 
        readonly=True, 
        default=_get_current_time_string
    )
    end_time = fields.Char(
        string="WO Finishing Time", 
        readonly=True, 
        default=False  # No default, will be set when button is pressed
    )
    workplace = fields.Selection(
        [
            ("inside", "Workshop"),
            ("outside", "External"),
        ],
        string="Service Location",
        default="inside",
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
    glass_destination = fields.Many2one(
        "vehicle.glass", string="Glass Position", required=True
    )
    invoice_number = fields.Char(string="Invoice Number", required=True)

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

    # Onchange methods
    @api.onchange("service_type")
    def _onchange_service_type(self):
        """Reset related fields when service type changes"""
        for rec in self:
            if rec.service_type == "service":
                rec.glass_option = False
                rec.retailer_type = False
            elif rec.service_type == "glass_sale":
                rec.service_option = False
                rec.retailer_type = False

    @api.onchange("glass_option")
    def _onchange_glass_option(self):
        """Reset retailer type when glass option changes"""
        for rec in self:
            if rec.glass_option != "retailer_glass":
                rec.retailer_type = False

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
        # Get the current time in 12-hour format when button is pressed
        current_time = self._get_current_time_string()
        self.write({
            "status": "done",
            "end_time": current_time,  # Record the current time when button is pressed
        })
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "list,form",
            "domain": [("status", "=", "done")],
            "target": "current",
        }

    # Constraint methods
    @api.constrains("phone")
    def _check_phone(self):
        """Validate phone number format"""
        for record in self:
            if record.phone and not re.fullmatch(r"\d{10}", record.phone):
                raise ValidationError(_("Phone number must be exactly 10 digits."))

    # Override methods
    def write(self, vals):
        """Block editing if status is done, except for Admins"""
        if any(rec.status == "done" for rec in self):
            if not self.env.user.has_group("base.group_system"):
                raise UserError(
                    _(
                        "You cannot edit a completed record. Please contact the administrator."
                    )
                )
        return super().write(vals)

    def unlink(self):
        """Block deleting if status is done, except for Admins"""
        if any(rec.status == "done" for rec in self):
            if not self.env.user.has_group("base.group_system"):
                raise UserError(
                    _(
                        "You cannot delete a completed record. Please contact the administrator."
                    )
                )
        return super().unlink()
    
    def name_get(self):
        result = []
        for rec in self:
            # Display all three fields in the dropdown
            name = f"{rec.vehicle_number or ''} / {rec.invoice_number or ''} / {rec.phone or ''}"
            result.append((rec.id, name))
        return result

    @api.model
    def name_search(self, name, args=None, operator="ilike", limit=100):
        args = args or []
        domain = args + [
            "|", "|",
            ("vehicle_number", operator, name),
            ("invoice_number", operator, name),
            ("phone", operator, name),
        ]
        records = self.search(domain, limit=limit)
        return records.name_get()