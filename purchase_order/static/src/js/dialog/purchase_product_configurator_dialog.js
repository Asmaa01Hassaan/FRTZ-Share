/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductMatrixDialog } from "@product_matrix/js/product_matrix_dialog";

console.log("PATCH FILE LOADED");

export class PurchaseProductConfiguratorDialog extends ProductMatrixDialog {
    static template = "purchase.ProductConfiguratorDialog";

    setup() {
        super.setup?.();

        // Props افتراضية لضمان التشغيل بدون error
        this.props.rows = this.props.rows || [];
        this.props.record = this.props.record || {};
        this.props.product_template_id = this.props.product_template_id || 0;
    }

    _onConfirm() {
        const inputs = document.getElementsByClassName('o_matrix_input');
        let matrixChanges = [];
        for (let i = 0; i < inputs.length; i++) {
            const value = parseFloat(inputs[i].value || 0);
            if (value > 0) {
                matrixChanges.push({
                    qty: value,
                    ptav_ids: [i],
                });
            }
        }
        if (matrixChanges.length > 0) {
            this.props.record.update({
                grid: JSON.stringify({
                    changes: matrixChanges,
                    product_template_id: this.props.product_template_id,
                }),
                grid_update: true,
            });
        }
        this.props.close();
    }
}

//ProductMatrixDialog.prototype.constructor.template = "sale.ProductConfiguratorDialog";

