# -*- coding: utf-8 -*-
{
    "name": "Timeoff Roles",
    "summary": "Custom approval workflow (Branch Manager - Manager - CEO) for time off requests.",
    "description": """
Custom Time Off Roles & Approval Workflow
=========================================

Roles
-----
* Time Off: Employee        Create and manage own leave only.
* Time Off: Branch Manager First-level approver.
* Time Off: Manager         Second-level approver.
* Time Off: HR             Full admin; can approve at any stage.
* Time Off: CEO             Final approver; full admin visibility.

Workflow
--------
Draft - Branch Manager - Manager - CEO - Approved
                                       - Cancelled (any stage)

Both the employee "My Time Off" form and the admin "All Time Off" form
show the same statusbar and the same context-sensitive action buttons,
so every role sees a consistent interface.
    """,
    "author": "Dishan Shrestha",
    "website": "https://www.dishanshrestha.com.np",
    "category": "Human Resources",
    "version": "0.3",
    "depends": ["base", "hr_holidays",],
    "data": [
        "security/time_off_roles.xml",
        "security/ir.model.access.csv",
        "views/hr_leave_views.xml",
        'views/hr_leave_refuse_reason_wizard_views.xml',
    ],
    "license": "LGPL-3",
    "installable": True,
    "auto_install": False,
    "application": True,
}
