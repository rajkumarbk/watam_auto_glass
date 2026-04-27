from odoo import models, fields


class LaptopRecords(models.Model):
    _name = "laptop.records"
    _description = "Laptop Records"

    employee_id = fields.Many2one("hr.employee", string="Employee")
    brand = fields.Char(string="Brand")
    model = fields.Char(string="Model")
    serial_number = fields.Char(string="Serial Number")
    issue_date = fields.Date(string="Issue Date")


class CarRecords(models.Model):
    _name = "car.records"
    _description = "Car Records"

    employee_id = fields.Many2one("hr.employee", string="Employee")
    brand = fields.Char(string="Brand")
    model = fields.Char(string="Model")
    plate_number = fields.Char(string="Plate Number")
    vin_number = fields.Char(string="VIN Number")
    issue_date = fields.Date(string="Issue Date")


class OtherRecords(models.Model):
    _name = "other.records"
    _description = "Other Records"

    employee_id = fields.Many2one("hr.employee", string="Employee")
    item_name = fields.Char(string="Item Name")
    item_description = fields.Text(string="Item Description")
    issue_date = fields.Date(string="Issue Date")


class AssetDetails(models.Model):
    _name = "asset.details"
    _description = "Asset Details"

    employee_id = fields.Many2one("hr.employee", string="Employee")
    asset_id = fields.Char(
        string="Asset ID", readonly=True, copy=False, default=lambda self: "New"
    )

    asset_type = fields.Selection(
        [
            ("office", "Office Equipment"),
            ("vehicle", "Vehicle"),
            ("it", "IT / Technical Equipment"),
            ("cash", "Cash"),
            ("documents", "Documents / Records"),
            ("special", "Special / Other"),
            ("tools", "Tools / Equipment"),
        ],
        string="Asset Type",
        required=True,
    )

    date_received = fields.Date(string="Date Received")
    condition_at_receipt = fields.Selection(
        [
            ("new", "New"),
            ("used", "Used"),
        ],
        string="Condition at Receipt",
        required=True,
    )
    asset_description = fields.Text(string="Asset Description")

    employee_signature = fields.Binary(string="Employee Signature")
    employee_signature_name = fields.Char(string="Employee Signature Filename")
    manager_signature = fields.Binary(string="Manager Signature")
    manager_signature_name = fields.Char(string="Manager Signature Filename")
    notes = fields.Text(string="Additional Notes")


class AssetReturn(models.Model):
    _name = "asset.return"
    _description = "Asset Returns"

    employee_id = fields.Many2one("hr.employee", string="Employee")
    expected_return_date = fields.Date(string="Expected Return Date")
    actual_return_date = fields.Date(string="Actual Return Date")

    condition_at_return = fields.Selection(
        [
            ("excellent", "Excellent"),
            ("good", "Good"),
            ("bad", "Bad"),
        ],
        string="Condition at Return",
        required=True,
    )

    employee_signature = fields.Binary(string="Employee Signature")
    employee_signature_name = fields.Char(string="Employee Signature Filename")
    manager_signature = fields.Binary(string="Manager Signature")
    manager_signature_name = fields.Char(string="Manager Signature Filename")

    notes = fields.Text(string="Additional Notes")


class CrnMaster(models.Model):
    _name = "crn.master"
    _description = "CRN Master"

    name = fields.Char(string="CRN", required=True)

    _sql_constraints = [("crn_unique", "unique(name)", "CRN must be unique.")]


# NEW: Main Equipment Model to hold both Asset Details and Returns
class EquipmentRecord(models.Model):
    _name = "equipment.record"
    _description = "Equipment Record"
    _rec_name = "employee_id"

    employee_id = fields.Many2one("hr.employee", string="Employee", required=True)

    # One2many relationship to Asset Details
    asset_details_ids = fields.One2many(
        "asset.details", "equipment_record_id", string="Asset Details"
    )

    # One2many relationship to Asset Returns
    asset_return_ids = fields.One2many(
        "asset.return", "equipment_record_id", string="Asset Returns"
    )


# Update AssetDetails model to link to EquipmentRecord
class AssetDetails(models.Model):
    _inherit = "asset.details"

    equipment_record_id = fields.Many2one("equipment.record", string="Equipment Record")


# Update AssetReturn model to link to EquipmentRecord
class AssetReturn(models.Model):
    _inherit = "asset.return"

    equipment_record_id = fields.Many2one("equipment.record", string="Equipment Record")
