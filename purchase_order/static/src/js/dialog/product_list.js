/** @odoo-module **/
import { ProductMatrixDialog } from "@product_matrix/js/product_matrix_dialog";
import { PurchaseProductConfiguratorDialog } from "purchase_order/static/src/js/dialog/purchase_product_configurator_dialog";

const OriginalConstructor = ProductMatrixDialog.prototype.constructor;

ProductMatrixDialog.prototype.constructor = function (...args) {
    return new PurchaseProductConfiguratorDialog(...args);
};

console.log("✅ Any instance of ProductMatrixDialog now uses the new Purchase template");
