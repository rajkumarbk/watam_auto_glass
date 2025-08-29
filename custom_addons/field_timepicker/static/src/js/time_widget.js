/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useInputField } from "@web/views/fields/input_field_hook";
const { Component, useRef, onMounted } = owl;
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

/**
 * Define this module for the function of creating a time picker widget
 */
export class FieldTimePicker extends Component {
    static template = 'FieldTimePicker';

    setup() {
        this.input = useRef('input_time');
        // Ensure the element is accessible after the component is mounted
        onMounted(() => {
            if (!this.input.el) {
                console.error("Input element is not available.");
            }
        });
        useInputField({
            getValue: () => this.props.record.data[this.props.name] || "",
            refName: "input_time"
        });
    }
    /**
     * Function to open a time picker and set the time.
     */
    _onClickTimeField(ev) {
        const timePicker = this.input.el;
        if (!timePicker) {
            console.error("Input element is not available.");
            return;
        }
        if (this.props.record.fields[this.props.name].type === "char" && timePicker) {
            const currentTime = timePicker.value || "00:00:00";
            const [hour, minute, second] = currentTime.split(':').map(Number);
            // Create a container for the time picker near the input field
            const timePickerContainer = document.createElement("div");
            timePickerContainer.className = "time-picker-container";
            document.body.appendChild(timePickerContainer);
            // Position the time picker container relative to the input field
            const rect = timePicker.getBoundingClientRect();
            timePickerContainer.style.position = "absolute";
            timePickerContainer.style.top = `${rect.bottom + window.scrollY}px`;
            timePickerContainer.style.left = `${rect.left + window.scrollX}px`;
            const createTimeBox = (label, value, max) => {
                const wrapper = document.createElement("div");
                wrapper.className = "time-box-wrapper";
                const incrementButton = document.createElement("button");
                incrementButton.textContent = "+";
                incrementButton.className = "time-box-button";
                wrapper.appendChild(incrementButton);
                const display = document.createElement("div");
                display.textContent = value < 10 ? `0${value}` : value;
                display.className = "time-box-display";
                wrapper.appendChild(display);
                const decrementButton = document.createElement("button");
                decrementButton.textContent = "-";
                decrementButton.className = "time-box-button";
                wrapper.appendChild(decrementButton);
                incrementButton.addEventListener("click", () => {
                    let newValue = (parseInt(display.textContent, 10) + 1) % (max + 1);
                    display.textContent = newValue < 10 ? `0${newValue}` : newValue;
                });
                decrementButton.addEventListener("click", () => {
                    let newValue = (parseInt(display.textContent, 10) - 1 + (max + 1)) % (max + 1);
                    display.textContent = newValue < 10 ? `0${newValue}` : newValue;
                });
                return wrapper;
            };
            const hourBox = createTimeBox("Hour", hour, 23);
            const minuteBox = createTimeBox("Minute", minute, 59);
            const secondBox = createTimeBox("Second", second, 59);
            timePickerContainer.appendChild(hourBox);
            timePickerContainer.appendChild(minuteBox);
            timePickerContainer.appendChild(secondBox);
            const confirmButton = document.createElement("button");
            confirmButton.textContent = _t("Set Time");
            confirmButton.className = "time-picker-confirm-button";
            timePickerContainer.appendChild(confirmButton);
            confirmButton.addEventListener("click", () => {
                if (this.input?.el) {
                    const selectedTime = `${hourBox.querySelector('.time-box-display').textContent}:${minuteBox.querySelector('.time-box-display').textContent}:${secondBox.querySelector('.time-box-display').textContent}`;
                    this.input.el.value = selectedTime;
                    this.props.record.update({
                        [this.props.name]: selectedTime
                    });
                    document.body.removeChild(timePickerContainer);
                } else {
                    document.body.removeChild(timePickerContainer);
                }
            });
        } else {
            this.env.model.dialog.add(AlertDialog, {
                body: _t("This widget can only be added to 'Char' field"),
            });
        }
    }
}
FieldTimePicker.props = {
    ...standardFieldProps,
};
export const TimePickerField = {
    component: FieldTimePicker,
    supportedTypes: ["char"],
};
registry.category("fields").add("timepicker", TimePickerField);