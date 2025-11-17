/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

/**
 * Document Manager JavaScript
 * Enhances user experience for document management
 */

// File preview functionality
export function previewDocument(attachmentId) {
    const url = `/web/content/${attachmentId}?download=false`;
    window.open(url, '_blank', 'width=1200,height=800');
}

// File download functionality  
export function downloadDocument(attachmentId, filename) {
    const url = `/web/content/${attachmentId}?download=true`;
    const link = document.createElement('a');
    link.href = url;
    link.download = filename || 'file';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Category color helper
export function getCategoryColor(colorIndex) {
    const colors = [
        '#95a5a6', // 0 - Gray
        '#3498db', // 1 - Blue
        '#e74c3c', // 2 - Red
        '#f39c12', // 3 - Orange
        '#16a085', // 4 - Teal
        '#9b59b6', // 5 - Purple
        '#34495e', // 6 - Dark Gray
        '#27ae60', // 7 - Green
        '#95a5a6', // 8 - Gray
        '#e67e22', // 9 - Dark Orange
        '#2ecc71', // 10 - Light Green
    ];
    return colors[colorIndex] || colors[0];
}

// Document upload handler with category
export function uploadWithCategory(resModel, resId, categoryId) {
    // This will be handled by Odoo's file upload mechanism
    // Just ensuring the category is set in context
    return {
        context: {
            default_res_model: resModel,
            default_res_id: resId,
            default_document_category_id: categoryId,
        }
    };
}

// Filter documents by category
export function filterByCategory(categoryCode) {
    return {
        domain: [['document_category_id.code', '=', categoryCode]],
        context: {
            search_default_group_by_category: 1,
        }
    };
}

// Export all utilities
export default {
    previewDocument,
    downloadDocument,
    getCategoryColor,
    uploadWithCategory,
    filterByCategory,
};

