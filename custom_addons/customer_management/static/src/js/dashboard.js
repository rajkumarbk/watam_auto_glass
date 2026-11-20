/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CmChart } from "./chart_card";

const PERIODS = [
    { key: "today", label: "Today" },
    { key: "yesterday", label: "Yesterday" },
    { key: "this_week", label: "This Week" },
    { key: "last_week", label: "Last Week" },
    { key: "this_month", label: "This Month" },
    { key: "last_month", label: "Last Month" },
    { key: "this_year", label: "This Year" },
    { key: "custom", label: "Custom Range" },
];

export class CustomerDashboard extends Component {
    static template = "customer_management.Dashboard";
    static components = { CmChart };
    setup() {
        this.orm = useService("orm");
        this.periods = PERIODS;
        this.state = useState({
            loading: true,
            showFilters: false,
            filters: {
                period: "this_month",
                company_id: "",
                branch_id: "",
                date_from: "",
                date_to: "",
            },
            options: { companies: [], branches: [] },
            data: { ongoing: 0, done: 0, top_employee: null, charts: {} },
        });
        onWillStart(async () => {
            this.state.options = await this.orm.call(
                "customer.dashboard",
                "get_filter_options",
                []
            );
            await this.load();
        });
    }

    get branches() {
        const cid = parseInt(this.state.filters.company_id);
        return this.state.options.branches.filter(
            (b) => !cid || b.company_id === cid
        );
    }

    get periodLabel() {
        const p = PERIODS.find((x) => x.key === this.state.filters.period);
        return p ? p.label : "";
    }

    async load() {
        const f = this.state.filters;
        if (f.period === "custom" && (!f.date_from || !f.date_to)) {
            return;
        }
        this.state.loading = true;
        this.state.data = await this.orm.call(
            "customer.dashboard",
            "get_dashboard_data",
            [],
            {
                filters: {
                    period: f.period,
                    date_from: f.date_from || false,
                    date_to: f.date_to || false,
                    company_id: f.company_id ? parseInt(f.company_id) : false,
                    branch_id: f.branch_id ? parseInt(f.branch_id) : false,
                },
            }
        );
        this.state.loading = false;
    }

    toggleFilters() {
        this.state.showFilters = !this.state.showFilters;
    }

    setPeriod(key) {
        this.state.filters.period = key;
        this.load();
    }

    onCompanyChange() {
        this.state.filters.branch_id = "";
        this.load();
    }

    onChange() {
        this.load();
    }
}

registry.category("actions").add("customer_management.dashboard", CustomerDashboard);