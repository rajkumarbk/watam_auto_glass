/** @odoo-module **/
import { Component, onMounted, onPatched, onWillStart, onWillUnmount, useRef } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";

const PALETTE = [
    "#4f46e5", "#14b8a6", "#f59e0b", "#f43f5e", "#0ea5e9",
    "#8b5cf6", "#10b981", "#fb923c", "#ec4899", "#64748b",
];

export class CmChart extends Component {
    static template = "customer_management.CmChart";
    static props = {
        title: String,
        type: String, // line | bar | hbar | doughnut
        data: Array, // [{label, value}]
    };

    setup() {
        this.canvas = useRef("canvas");
        this.chart = null;
        onWillStart(() => loadBundle("web.chartjs_lib"));
        onMounted(() => this.draw());
        onPatched(() => this.draw());
        onWillUnmount(() => this.chart && this.chart.destroy());
    }

    get colors() {
        const n = this.props.data.length;
        return Array.from({ length: n }, (_, i) => PALETTE[i % PALETTE.length]);
    }

    draw() {
        const labels = this.props.data.map((d) => d.label);
        const values = this.props.data.map((d) => d.value);
        const type = this.props.type;

        if (this.chart) {
            const ds = this.chart.data.datasets[0];
            this.chart.data.labels = labels;
            ds.data = values;
            if (type === "bar" || type === "hbar" || type === "doughnut") {
                ds.backgroundColor = this.colors;
            }
            this.chart.update();
            return;
        }

        Chart.defaults.color = getComputedStyle(document.body).color;
        Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;

        const isDoughnut = type === "doughnut";
        const dataset = { data: values };
        if (type === "line") {
            Object.assign(dataset, {
                borderColor: PALETTE[0],
                backgroundColor: "rgba(79, 70, 229, 0.12)",
                fill: true,
                tension: 0.35,
                pointRadius: 2,
                borderWidth: 2,
            });
        } else {
            Object.assign(dataset, {
                backgroundColor: this.colors,
                borderWidth: isDoughnut ? 0 : 0,
                borderRadius: isDoughnut ? 0 : 6,
            });
        }

        this.chart = new Chart(this.canvas.el, {
            type: type === "hbar" ? "bar" : type,
            data: { labels, datasets: [dataset] },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: type === "hbar" ? "y" : "x",
                cutout: isDoughnut ? "65%" : undefined,
                plugins: {
                    legend: {
                        display: isDoughnut,
                        position: "bottom",
                        labels: { usePointStyle: true, boxWidth: 8 },
                    },
                },
                scales: isDoughnut
                    ? {}
                    : {
                        x: { grid: { display: type === "hbar" }, ticks: { precision: 0 } },
                        y: { beginAtZero: true, ticks: { precision: 0 } },
                    },
            },
        });
    }
}