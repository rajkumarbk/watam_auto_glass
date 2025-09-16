from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime
import pytz
import re
from odoo.exceptions import UserError


class ClientRecord(models.Model):
    _name = "customer.record"
    _description = "Customer Records"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "start_time desc"
    _rec_name = "vehicle_number"

    employee_id = fields.Many2one("hr.employee", string="Employee Name")
    assistant_staff = fields.Many2one("hr.employee", string="Secondary Technician")
    branch_id = fields.Many2one(
        "res.company",
        string="Branch Name",
        default=lambda self: self.env.company,
    )
    name = fields.Char(string="Customer Name", required=True)
    phone = fields.Char(string="Mobile Number", required=True)
    vehicle_brand = fields.Many2one("vehicle.brand", string="Car Brand", required=True)
    vehicle_model = fields.Many2one("vehicle.model", string="Car Name", required=True)
    manufactured_year_id = fields.Many2one(
        "manufactured.year", string="Car Model", required=True
    )

    vehicle_display = fields.Char(
        string="Vehicle Info",
        compute="_compute_vehicle_display",
    )

    vehicle_number = fields.Char(string="Car Registration Number", required=True)
    date = fields.Date(
        string="Date",
        default=fields.Date.context_today,
        readonly=True,
    )
    photo = fields.Binary(string="Photo")
    notes = fields.Text(string="Notes")

    def _get_current_time_float(self):
        tz = pytz.timezone("Asia/Riyadh")
        now = datetime.now(tz)
        return now.hour + now.minute / 60.0

    start_time = fields.Float(
        string=" WO Start Time", readonly=True, default=_get_current_time_float
    )
    end_time = fields.Float(string="WO Finishing Time", readonly=True)

    
            

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
        [("service", "Service"), ("glass_sale", "Glass Sale and Installation")],
        string="Service Type",
    )

    service_option = fields.Many2one("service.option", string="Service Option")

    glass_option = fields.Selection(
        [("our_glass", "Our Glass"), ("retailer_glass", "Retailer Glass")],
        string="Glass Sale Options",
    )

    retailer_type = fields.Selection(
        [("oem", "OEM"), ("aftermarket", "Aftermarket")], string="Retailer Glass Type"
    )
    glass_destination = fields.Many2one(
        "vehicle.glass", string="Glass Position", required=True
    )
    invoice_number = fields.Char(string="Invoice Number", required=True)

    @api.onchange("service_type")
    def _onchange_service_type(self):
        for rec in self:
            if rec.service_type == "service":
                rec.glass_option = False
                rec.retailer_type = False
            elif rec.service_type == "glass_sale":
                rec.service_option = False
                rec.retailer_type = False
            else:
                rec.service_option = False
                rec.glass_option = False
                rec.retailer_type = False

    @api.onchange("glass_option")
    def _onchange_glass_option(self):
        for rec in self:
            if rec.glass_option != "retailer_glass":
                rec.retailer_type = False

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

    def action_set_started(self):
        self.status = "started"
        return {
            "type": "ir.actions.act_window",
            "res_model": "customer.record",
            "view_mode": "list,form",
            "domain": [("status", "=", "started")],
            "target": "current",
        }

    def action_set_on_progress(self):
        """⚠️ Note: 'on_progress' is not in your selection.
        Either add it in `status` field or this will raise a ValueError."""
        self.status = "on_progress"
        
    def action_set_done(self):
        """Set status to done and record end_time"""
        for record in self:
            record.status = "done"
            record.end_time = self._get_current_time_float()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'customer.record',
            'view_mode': 'list,form',
            'domain': [('status', '=', 'done')],
            'target': 'current',
        }

    def action_set_done(self):
        """Set status to done and record end_time"""
        for record in self:
            record.status = "done"
            record.end_time = self._get_current_time_float()
        return {
            "type": "ir.actions.act_window",
            "res_model": "customer.record",
            "view_mode": "list,form",
            "domain": [("status", "=", "done")],
            "target": "current",
        }

    @api.constrains("phone")
    def _check_phone(self):
        for record in self:
            if record.phone and not re.fullmatch(r"\d{10}", record.phone):
                raise ValidationError(_("Phone number must be exactly 10 digits."))

    def write(self, vals):
        """Block editing if status = done, except for Admins."""
        for rec in self:
            if rec.status == "done" and not self.env.user.has_group(
                "base.group_system"
            ):
                raise UserError(
                    _(
                        "You cannot edit a completed record. Please contact the administrator."
                    )
                )
        return super().write(vals)

    def unlink(self):
        """Block deleting if status = done, except for Admins."""
        for rec in self:
            if rec.status == "done" and not self.env.user.has_group(
                "base.group_system"
            ):
                raise UserError(
                    _(
                        "You cannot delete a completed record. Please contact the administrator."
                    )
                )
        return super().unlink()

    # available_year_ids = fields.Many2many(
    #     "manufactured.year",
    #     string="Available Years",
    #     compute="_compute_available_years",
    # )

    # @api.depends("vehicle_model")
    # def _compute_available_years(self):
    #     for rec in self:
    #         rec.available_year_ids = rec.vehicle_model.manufactured_year_id
