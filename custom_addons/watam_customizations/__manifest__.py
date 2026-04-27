# -*- coding: utf-8 -*-
{
    "name": "watam_customizations",
    "summary": "Customizations for Watam Auto Glass",
    "description": """
Long description of module's purpose
    """,
    "author": "Watam Auto Glass",
    "website": "https://www.watamglass.com",
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    "category": "Human Resources",
    "version": "0.1",
    "sequence": 2,
    # any module necessary for this one to work correctly
    "depends": ["base", "hr", "hr_contract"],
    # always loaded
    "data": [
        "security/ir.model.access.csv",
        "views/views.xml",
        "views/hr_employee_inherit.xml",
        "views/hr_contract_inherit.xml",
        "views/hr_department_inherit.xml",
        "views/hr_job_inherit.xml",
        # "data/cron_jobs.xml",
        # "data/mail_template.xml",
        # 'views/templates.xml',
        # "views/asset_handover_views.xml",
        # "views/menu_items.xml",
    ],
    # only loaded in demonstration mode
    "demo": [
        "demo/demo.xml",
    ],
    "images": ["static/description/icon.png"],
    "license": "LGPL-3",
    "installable": True,
    "auto_install": False,
    "application": True,
}
