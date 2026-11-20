# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models

WEEK_START = 6  # 6 = Sunday (Saudi). Use 0 for Monday.


class CustomerDashboard(models.AbstractModel):
    _name = "customer.dashboard"
    _description = "Customer Record Dashboard"

    @api.model
    def _get_range(self, period, date_from=None, date_to=None):
        today = fields.Date.context_today(self)
        if period == "today":
            return today, today
        if period == "yesterday":
            d = today - timedelta(days=1)
            return d, d
        if period in ("this_week", "last_week"):
            start = today - timedelta(days=(today.weekday() - WEEK_START) % 7)
            if period == "last_week":
                start -= timedelta(days=7)
            return start, start + timedelta(days=6)
        if period == "this_month":
            start = today.replace(day=1)
            nxt = (start + timedelta(days=32)).replace(day=1)
            return start, nxt - timedelta(days=1)
        if period == "last_month":
            end = today.replace(day=1) - timedelta(days=1)
            return end.replace(day=1), end
        if period == "this_year":
            return today.replace(month=1, day=1), today.replace(month=12, day=31)
        if period == "custom" and date_from and date_to:
            return fields.Date.to_date(date_from), fields.Date.to_date(date_to)
        return self._get_range("this_month")

    @api.model
    def get_filter_options(self):
        Company = self.env["res.company"]
        companies = Company.search([("parent_id", "=", False)])
        branches = Company.search([("parent_id", "!=", False)])
        return {
            "companies": [{"id": c.id, "name": c.name} for c in companies],
            "branches": [
                {"id": b.id, "name": b.name, "company_id": b.parent_id.id}
                for b in branches
            ],
        }

    @api.model
    def get_dashboard_data(self, filters=None):
        filters = filters or {}
        d_from, d_to = self._get_range(
            filters.get("period", "this_month"),
            filters.get("date_from"),
            filters.get("date_to"),
        )
        domain = [("date", ">=", d_from), ("date", "<=", d_to)]
        if filters.get("branch_id"):
            domain.append(("branch_id", "=", int(filters["branch_id"])))
        elif filters.get("company_id"):
            domain.append(("branch_id", "child_of", int(filters["company_id"])))

        Rec = self.env["customer.record"]
        done_domain = domain + [("status", "=", "done")]

        counts = dict(Rec._read_group(domain, ["status"], ["__count"]))
        employees = self._group(Rec, done_domain, "employee_id", limit=10)

        # trend: day, or month if range is long
        monthly = (d_to - d_from).days > 92
        gran = "date:month" if monthly else "date:day"
        rows = Rec._read_group(domain, [gran], ["__count"], order=gran + " asc")
        fmt = "%b %Y" if monthly else "%d %b"
        trend = [{"label": d.strftime(fmt), "value": c} for d, c in rows if d]

        return {
            "date_from": fields.Date.to_string(d_from),
            "date_to": fields.Date.to_string(d_to),
            "ongoing": counts.get("started", 0),
            "done": counts.get("done", 0),
            "top_employee": (
                {"name": employees[0]["label"], "count": employees[0]["value"]}
                if employees
                else None
            ),
            "charts": {
                "trend": trend,
                "branch": self._group(Rec, domain, "branch_id", limit=15),
                "employee": employees,
                "service_type": self._group(Rec, domain, "service_type"),
                "complexity": self._group(Rec, domain, "service_complexity"),
                "retailer_type": self._group(Rec, domain, "retailer_type"),
                "brand": self._group(Rec, domain, "vehicle_brand", limit=10),
                "glass": self._group(Rec, domain, "glass_destination", limit=10),
            },
        }

    @api.model
    def _group(self, Rec, domain, field, limit=None):
        spec = Rec._fields[field]
        rows = Rec._read_group(
            domain, [field], ["__count"], order="__count desc", limit=limit
        )
        labels = (
            dict(spec._description_selection(self.env))
            if spec.type == "selection"
            else {}
        )
        out = []
        for val, count in rows:
            if not val:
                continue
            name = val.display_name if spec.type == "many2one" else labels.get(val, val)
            out.append({"label": name, "value": count})
        return out
