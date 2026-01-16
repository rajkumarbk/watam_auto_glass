from odoo import fields, models


class FingerprintTemplates(models.Model):
    """Inherit the model to add field"""

    _name = "fingerprint.templates"
    _description = "Finger Print Templates for Employee"

    employee_id = fields.Many2one(
        "hr.employee", string="Employee", help="Name of the Employee"
    )
    finger_id = fields.Char(
        string="Finger Id", help="The Number that refers the Finger"
    )
    filename = fields.Char(
        string="Finger File Name", help="File Name of the Uploaded Finger Print"
    )
    finger_template = fields.Binary(
        string="Finger Template", help="The Uploaded Finger Print file"
    )
