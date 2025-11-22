/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component } from "@odoo/owl";

export class SpotStatusWidget extends Component {
    static template = "rehal_air_cargo_digital_platform.SpotStatusWidget";
    static props = { ...standardFieldProps };
}

registry.category("fields").add("spot_status", SpotStatusWidget);

