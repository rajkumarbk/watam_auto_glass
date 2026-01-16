from odoo import _, fields, models


class HrEmployee(models.Model):
    """Inherit the model to add field"""

    _inherit = "hr.employee"

    device_id_num = fields.Char(
        string="Biometric Device ID", help="Give the biometric device id", copy=False
    )
    device_id = fields.Many2one(
        "biometric.device.details",
        copy=False,
        readonly=True,
        help="The biometric device details",
    )
    fingerprint_ids = fields.One2many(
        "fingerprint.templates",
        "employee_id",
        help="Store finger print templates of " "an employee",
    )

    def action_biometric_device(self):
        """Server Action for Biometric Device which open a wizard with
        several options"""
        return {
            "type": "ir.actions.act_window",
            "target": "new",
            "name": _("Biometric Management"),
            "view_mode": "form",
            "res_model": "employee.biometric",
            "context": {"default_employee_id": self.id},
        }
