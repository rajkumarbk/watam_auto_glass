from odoo import fields, models, api, _
from datetime import timedelta, datetime
import logging

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    passport_expiry = fields.Date(string="Passport Expiry Date")

    def _cron_check_passport_expiry(self):
        """
        Cron job to check passport expiry 60 days in advance
        Runs daily and sends email to employees whose passport expires in exactly 60 days
        """
        today = fields.Date.today()
        notify_date = today + timedelta(days=60)

        _logger.info(f"Running passport expiry check for date: {notify_date}")

        employees = self.search(
            [
                ("passport_expiry", "=", notify_date),
                ("private_email", "!=", False),
                ("passport_expiry", "!=", False),
            ]
        )

        _logger.info(
            f"Found {len(employees)} employees with passport expiring in 60 days"
        )

        template = self.env.ref(
            "watam_customizations.mail_template_passport_expiry",
            raise_if_not_found=False,
        )

        if not template:
            _logger.error("Email template 'mail_template_passport_expiry' not found!")
            return

        email_sent_count = 0
        for emp in employees:
            try:
                template.with_context(lang=emp.lang).send_mail(
                    emp.id,
                    force_send=True,
                    email_values={
                        "email_to": emp.private_email,
                    },
                )
                _logger.info(
                    f"Passport expiry email sent to {emp.name} ({emp.private_email})"
                )
                email_sent_count += 1
            except Exception as e:
                _logger.error(f"Failed to send email to {emp.name}: {str(e)}")

        _logger.info(f"Total emails sent: {email_sent_count}")

    birthplace = fields.Many2one("res.country", string="Birth Place")
    no_of_dependents = fields.Integer(string="Number of Dependents (if any)")
    alternative_mobile_number = fields.Char(string="Alternative Mobile Number")

    relationship_type = fields.Selection(
        [
            ("spouse", "Spouse"),
            ("child", "Child"),
            ("parent", "Parent"),
            ("sibling", "Sibling"),
            ("friend", "Friend"),
            ("other", "Other"),
        ],
        string="Relationship Type",
        default="parent",
    )

    crn_id = fields.Many2one("crn.master", string="CRN", help="Select or create CRN")
    iban_number = fields.Char(string="Bank Account Number(IBAN)")
    bank_id = fields.Many2one("res.bank", string="Bank Name")
    profession_in_iqama = fields.Many2one("hr.job", string="Profession in Iqama")

    id_iqama = fields.Binary(string="ID/Iqama")
    id_iqama_name = fields.Char(string="ID/Iqama Filename")
    passport = fields.Binary(string="Passport")
    passport_name = fields.Char(string="Passport Filename")
    bank_account = fields.Binary(string="Bank Account Copy")
    bank_account_name = fields.Char(string="Bank Account Filename")
    curriculum_vitae = fields.Binary(string="Curriculum Vitae(CV)")
    curriculum_vitae_name = fields.Char(string="Curriculum Vitae(CV) Filename")
    signature = fields.Binary(string="Signature")
    signature_name = fields.Char(string="Signature Filename")
    educational_certificate = fields.Binary(string="Educational Certificate")
    educational_certificate_name = fields.Char(
        string="Educational Certificate Filename"
    )
    driving_license = fields.Binary(string="Driving License")
    driving_license_name = fields.Char(string="Driving License Filename")

    id_iqama_expiry = fields.Date(string="ID/Iqama Expiry Date")

    basic_salary = fields.Float(string="Basic Salary")
    allowances = fields.Float(string="Allowances")

    join_date = fields.Date(string="Join Date")

    employee_id_custom = fields.Char(
        string="Employee ID",
        readonly=True,
        copy=False,
        index=True,
        default=lambda self: _("New"),
    )

    laptop_records_ids = fields.One2many(
        "laptop.records", "employee_id", string="Laptop Records"
    )
    car_records_ids = fields.One2many(
        "car.records", "employee_id", string="Car Records"
    )
    other_records_ids = fields.One2many(
        "other.records", "employee_id", string="Other Records"
    )
    asset_details_ids = fields.One2many("asset.details", "employee_id")
    asset_return_ids = fields.One2many("asset.return", "employee_id")

    is_laptop = fields.Boolean(string="Laptop")
    laptop_brand = fields.Char(string="Laptop Brand")
    laptop_model = fields.Char(string="Laptop Model")
    laptop_serial_number = fields.Char(string="Laptop Serial Number")
    laptop_issue_date = fields.Date(string="Laptop Issue Date")

    is_car = fields.Boolean(string="Car")
    car_brand = fields.Char(string="Car Brand")
    car_model = fields.Char(string="Car Model")
    car_plate_number = fields.Char(string="Car Plate Number")
    car_issue_date = fields.Date(string="Car Issue Date")
    car_vin_number = fields.Char(string="Car VIN Number")

    is_other = fields.Boolean(string="Other")
    other_item_name = fields.Char(string="Other Item Name")
    other_item_description = fields.Text(string="Other Item Description")
    other_item_issue_date = fields.Date(string="Other Item Issue Date")

    # Asset Details
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
        default="office",
    )

    date_received = fields.Date(string="Date Received")
    condition_at_receipt = fields.Selection(
        [
            ("new", "New"),
            ("used", "Used"),
        ],
        string="Condition at Receipt",
        default="new",
    )
    asset_description = fields.Text(string="Asset Description")

    employee_signature = fields.Binary(string="Employee Signature")
    employee_signature_name = fields.Char(string="Employee Signature Filename")
    manager_signature = fields.Binary(string="Manager Signature")
    manager_signature_name = fields.Char(string="Manager Signature Filename")
    notes = fields.Text(string="Additional Notes")

    # Handover & Return
    expected_return_date = fields.Date(string="Expected Return Date")
    actual_return_date = fields.Date(string="Actual Return Date")

    condition_at_return = fields.Selection(
        [
            ("excellent", "Excellent"),
            ("good", "Good"),
            ("bad", "Bad"),
        ],
        string="Condition at Return",
        default="good",
    )

    @api.model
    def create(self, vals):
        """Override create method to generate employee ID sequence"""
        if vals.get("employee_id_custom", _("New")) == _("New"):

            department_id = vals.get("department_id", False)
            department_sequence = ""
            if department_id:
                department = self.env["hr.department"].browse(department_id)
                if department and department.department_sequence:
                    department_sequence = department.department_sequence

            country_id = vals.get("country_id", False)
            country_code = ""
            if country_id:
                country = self.env["res.country"].browse(country_id)
                if country and country.name:

                    country_code = country.name[:3].upper()

            join_date_str = vals.get("join_date", False)
            year_code = ""
            if join_date_str:
                try:

                    if isinstance(join_date_str, str):
                        join_date_obj = datetime.strptime(
                            join_date_str, "%Y-%m-%d"
                        ).date()
                    else:

                        join_date_obj = join_date_str

                    year_code = str(join_date_obj.year)[-2:]
                except (ValueError, AttributeError, TypeError) as e:
                    _logger.error(f"Error parsing join date {join_date_str}: {str(e)}")
                    year_code = "00"

            prefix = f"{year_code}{department_sequence.zfill(2)}{country_code}"
            all_employees = self.search(
                [
                    ("employee_id_custom", "!=", "New"),
                    ("employee_id_custom", "!=", False),
                ]
            )
            max_seq = 0
            for emp in all_employees:
                if emp.employee_id_custom:
                    import re

                    match = re.search(r"(\d{3})$", emp.employee_id_custom)
                    if match:
                        try:
                            seq_num = int(match.group(1))
                            if seq_num > max_seq:
                                max_seq = seq_num
                        except ValueError:
                            continue

            next_seq = max_seq + 1
            vals["employee_id_custom"] = f"{prefix}{next_seq:03d}"
        return super(HrEmployee, self).create(vals)

    def write(self, vals):
        if "job_id" in vals and "department_id" not in vals and vals.get("job_id"):
            job = self.env["hr.job"].browse(vals["job_id"])
            if job.department_id:
                vals["department_id"] = job.department_id.id
        return super(HrEmployee, self).write(vals)

    @api.onchange("job_id")
    def _onchange_job_id(self):
        if self.job_id and self.job_id.department_id:
            self.department_id = self.job_id.department_id

    @api.onchange("department_id", "country_id", "join_date")
    def _onchange_employee_id_generation_fields(self):
        """Update employee ID preview when relevant fields change"""
        if self.department_id and self.country_id and self.join_date:
            department_sequence = self.department_id.department_sequence or ""
            country_code = (
                self.country_id.name[:3].upper() if self.country_id.name else ""
            )
            year_code = ""
            if self.join_date:
                try:
                    join_date_obj = self.join_date
                    if isinstance(join_date_obj, str):
                        join_date_obj = datetime.strptime(
                            join_date_obj, "%Y-%m-%d"
                        ).date()
                    year_code = str(join_date_obj.year)[-2:]
                except (ValueError, AttributeError, TypeError):
                    year_code = "00"
            prefix = f"{year_code}{department_sequence.zfill(2)}{country_code}"
            all_employees = self.search(
                [
                    ("employee_id_custom", "!=", "New"),
                    ("employee_id_custom", "!=", False),
                    ("id", "!=", self.id),
                ]
            )
            max_seq = 0
            import re

            for emp in all_employees:
                if emp.employee_id_custom:
                    match = re.search(r"(\d{3})$", emp.employee_id_custom)
                    if match:
                        try:
                            seq_num = int(match.group(1))
                            if seq_num > max_seq:
                                max_seq = seq_num
                        except ValueError:
                            continue
            next_seq = max_seq + 1
            preview_id = f"{prefix}{next_seq:03d}"
            return {
                "warning": {
                    "title": "Employee ID Preview",
                    "message": f"Employee ID will be: {preview_id}",
                }
            }


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    passport_expiry = fields.Date(string="Passport Expiry Date")

    no_of_dependents = fields.Integer(string="Number of Dependents (if any)")
    alternative_mobile_number = fields.Char(string="Alternative Mobile Number")

    relationship_type = fields.Selection(
        [
            ("spouse", "Spouse"),
            ("child", "Child"),
            ("parent", "Parent"),
            ("sibling", "Sibling"),
            ("friend", "Friend"),
            ("other", "Other"),
        ],
        string="Relationship Type",
        default="parent",
    )

    crn_id = fields.Many2one("crn.master", string="CRN", help="Select or create CRN")
    iban_number = fields.Char(string="Bank Account Number(IBAN)")
    bank_id = fields.Many2one("res.bank", string="Bank Name")
    profession_in_iqama = fields.Many2one("hr.job", string="Profession in Iqama")

    id_iqama_name = fields.Char(string="ID/Iqama Filename")
    passport_name = fields.Char(string="Passport Filename")
    bank_account_name = fields.Char(string="Bank Account Filename")
    curriculum_vitae_name = fields.Char(string="Curriculum Vitae(CV) Filename")
    signature_name = fields.Char(string="Signature Filename")
    educational_certificate_name = fields.Char(
        string="Educational Certificate Filename"
    )
    driving_license_name = fields.Char(string="Driving License Filename")

    id_iqama_expiry = fields.Date(string="ID/Iqama Expiry Date")

    basic_salary = fields.Float(string="Basic Salary")
    allowances = fields.Float(string="Allowances")

    join_date = fields.Date(string="Join Date")

    employee_id_custom = fields.Char(string="Employee ID")

    laptop_records_ids = fields.One2many(
        "laptop.records", "employee_id", string="Laptop Records"
    )
    car_records_ids = fields.One2many(
        "car.records", "employee_id", string="Car Records"
    )
    asset_details_ids = fields.One2many("asset.details", "employee_id")
    asset_return_ids = fields.One2many("asset.return", "employee_id")

    is_laptop = fields.Boolean(string="Laptop", default=False)
    laptop_brand = fields.Char(string="Laptop Brand")
    laptop_model = fields.Char(string="Laptop Model")
    laptop_serial_number = fields.Char(string="Laptop Serial Number")
    laptop_issue_date = fields.Date(string="Laptop Issue Date")

    is_car = fields.Boolean(string="Car", default=False)
    car_brand = fields.Char(string="Car Brand")
    car_model = fields.Char(string="Car Model")
    car_plate_number = fields.Char(string="Car Plate Number")
    car_issue_date = fields.Date(string="Car Issue Date")
    car_vin_number = fields.Char(string="Car VIN Number")

    is_other = fields.Boolean(string="Other")
    other_item_name = fields.Char(string="Other Item Name")
    other_item_description = fields.Text(string="Other Item Description")
    other_item_issue_date = fields.Date(string="Other Item Issue Date")

    # Asset Details
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
        default="office",
    )

    date_received = fields.Date(string="Date Received")
    condition_at_receipt = fields.Selection(
        [
            ("new", "New"),
            ("used", "Used"),
        ],
        string="Condition at Receipt",
        default="new",
    )
    asset_description = fields.Text(string="Asset Description")
    employee_signature = fields.Binary(
        related="employee_id.employee_signature", readonly=True
    )
    employee_signature_name = fields.Char(
        related="employee_id.employee_signature_name", readonly=True
    )
    manager_signature = fields.Binary(
        related="employee_id.manager_signature", readonly=True
    )
    manager_signature_name = fields.Char(
        related="employee_id.manager_signature_name", readonly=True
    )
    notes = fields.Text(string="Additional Notes")

    # Handover & Return
    expected_return_date = fields.Date(string="Expected Return Date")
    actual_return_date = fields.Date(string="Actual Return Date")

    condition_at_return = fields.Selection(
        [
            ("excellent", "Excellent"),
            ("good", "Good"),
            ("bad", "Bad"),
        ],
        string="Condition at Return",
        default="good",
    )
    device_id_num = fields.Char(related="employee_id.device_id_num", readonly=True)
    device_id = fields.Many2one(
        "biometric.device.details", related="employee_id.device_id", readonly=True
    )
    birthplace = fields.Many2one(
        "res.country", related="employee_id.birthplace", readonly=True
    )
