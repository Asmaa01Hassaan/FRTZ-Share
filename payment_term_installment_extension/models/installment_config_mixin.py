# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.tools.misc import str2bool

INSTALLMENT_SCOPE_VALUES = {'per_invoice', 'per_lines'}
INSTALLMENT_BASELINE_DATE_VALUES = {'invoice_date', 'posting_date', 'receipt_date'}
INSTALLMENT_FIELD_DISPLAY_VALUES = {'visible', 'readonly', 'invisible'}


class InstallmentConfigMixin(models.AbstractModel):
    """Shared installment configuration helpers (no fields — call via env)."""
    _name = 'installment.config.mixin'
    _description = 'Installment Scope and Baseline Date Configuration'

    @api.model
    def _get_field_display_mode(self, icp, param_name, legacy_show_param):
        mode = icp.get_param(param_name)
        if mode in INSTALLMENT_FIELD_DISPLAY_VALUES:
            return mode
        show = str2bool(icp.get_param(legacy_show_param, 'True'), default=True)
        return 'visible' if show else 'invisible'

    @api.model
    def _get_installment_ui_config(self):
        icp = self.env['ir.config_parameter'].sudo()
        default_scope = icp.get_param(
            'payment_term_installment_extension.default_scope',
            'per_lines',
        )
        default_baseline_date = icp.get_param(
            'payment_term_installment_extension.default_baseline_date',
            'invoice_date',
        )
        if default_scope not in INSTALLMENT_SCOPE_VALUES:
            default_scope = 'per_lines'
        if default_baseline_date not in INSTALLMENT_BASELINE_DATE_VALUES:
            default_baseline_date = 'invoice_date'
        scope_display = self._get_field_display_mode(
            icp,
            'payment_term_installment_extension.scope_display',
            'payment_term_installment_extension.show_scope',
        )
        baseline_date_display = self._get_field_display_mode(
            icp,
            'payment_term_installment_extension.baseline_date_display',
            'payment_term_installment_extension.show_baseline_date',
        )
        return {
            'default_scope': default_scope,
            'default_baseline_date': default_baseline_date,
            'scope_display': scope_display,
            'baseline_date_display': baseline_date_display,
        }

    @api.model
    def _get_installment_default_scope(self):
        return self._get_installment_ui_config()['default_scope']

    @api.model
    def _get_installment_default_baseline_date(self):
        return self._get_installment_ui_config()['default_baseline_date']

    @api.model
    def _apply_installment_config_defaults(self, fields_list, values):
        config = self._get_installment_ui_config()
        if 'scope' in fields_list and 'scope' not in values:
            values['scope'] = config['default_scope']
        if 'baseline_date' in fields_list and 'baseline_date' not in values:
            values['baseline_date'] = config['default_baseline_date']
        if 'apply_payment_term_per_line' in fields_list and 'apply_payment_term_per_line' not in values:
            scope = values.get('scope', config['default_scope'])
            values['apply_payment_term_per_line'] = scope == 'per_lines'
        return values

    @api.model
    def _get_installment_field_ui_states(self):
        config = self._get_installment_ui_config()
        scope_mode = config['scope_display']
        baseline_mode = config['baseline_date_display']
        return {
            'show_installment_scope': scope_mode != 'invisible',
            'readonly_installment_scope': scope_mode == 'readonly',
            'show_installment_baseline_date': baseline_mode != 'invisible',
            'readonly_installment_baseline_date': baseline_mode == 'readonly',
        }
