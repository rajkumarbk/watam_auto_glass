# -*- coding: utf-8 -*-
{
    "name": "CRM - Customer Management",
    "summary": "Short (1 phrase/line) summary of the module's purpose",
    "description": """
Long description of module's purpose
    """,
    "author": "Watam And Salem",
    "category": "Human Resource",
    "version": "0.1",
    "sequence": 1,
    # any module necessary for this one to work correctly
    "depends": ["base", "hr", "hide_menu_user", "web"],
    # always loaded
    "data": [
        "security/security_group.xml",
        "security/ir.model.access.csv",
        "data/vehicle_brand_data.xml",
        "data/vehicle_model_data.xml",
        "data/manufactured_year.xml",
        "data/glass_data.xml",
        "data/problem_data.xml",
        "data/solution_data.xml",
        "data/service_data.xml",
        "reports/reports.xml",
        "views/master_data/vehicle_brand.xml",
        "views/master_data/vehicle_model.xml",
        "views/master_data/vehicle_manufactured_year.xml",
        "views/master_data/vehicle_glass.xml",
        "views/master_data/what_problem.xml",
        "views/master_data/what_solution.xml",
        "views/customer_record.xml",
        "views/problem_solution.xml",
        "views/evaluation_criteria.xml",
        "views/views.xml",
        "views/templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "customer_management/static/src/css/style.css",
            # 'customer_management/static/srcjs/camera_widget.js',
            # 'customer_management/static/src/xml/camera_widget.xml',
        ],
    },
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
