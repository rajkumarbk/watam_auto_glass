/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, useRef } from "@odoo/owl";

class CameraWidget extends Component {
    setup() {
        this.videoRef = useRef("video");
        this.canvasRef = useRef("canvas");
    }

    async startCamera() {
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({ video: true });
            this.videoRef.el.srcObject = this.stream;
        } catch (err) {
            alert("Camera access denied!");
        }
    }

    capture() {
        const canvas = this.canvasRef.el;
        const video = this.videoRef.el;
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext("2d").drawImage(video, 0, 0);

        const dataUrl = canvas.toDataURL("image/png");
        const base64 = dataUrl.split(",")[1];
        this.props.update(base64);
    }

    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
        }
    }
}

CameraWidget.template = "camera_widget_template";
CameraWidget.props = { ...standardFieldProps };

registry.category("fields").add("camera_widget", CameraWidget);
