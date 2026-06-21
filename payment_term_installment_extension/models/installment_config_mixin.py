# -*- coding: utf-8 -*-
from odoo import api, models, _
from odoo.exceptions import ValidationError
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

    @api.model
    def _build_installment_line_commands(self, term_values):
        """Build account.payment.term.line commands for a per-line installment term.

        This is a pure function of ``term_values`` (it reads no record state), so
        account.move.line and sale.order.line both delegate here to guarantee the
        EXACT same per-line installment schedule. The logic is unchanged from the
        two previously-duplicated ``_build_line_payment_term_commands`` methods —
        same checks, same ``round(..., 6)`` precision, same day intervals.

        Expected keys in ``term_values``: pay_type, installment_count,
        first_payment_type, first_payment_percentage, installment_frequency, and
        optionally line_amount.
        """
        pay_type = term_values['pay_type']
        installment_count = int(term_values['installment_count'] or 0)
        first_payment_type = term_values['first_payment_type']
        first_payment = term_values['first_payment_percentage'] or 0.0
        line_amount = term_values.get('line_amount') or 0.0

        if first_payment_type == 'percent' and not (0 <= first_payment <= 100):
            raise ValidationError(_("First Payment (%) must be between 0 and 100."))

        if pay_type == 'spot':
            return [(0, 0, {
                'value': 'percent',
                'value_amount': 100.0,
                'nb_days': 0,
                'delay_type': 'days_after',
            })]

        if pay_type != 'fixed' or installment_count < 1:
            return [(0, 0, {
                'value': 'percent',
                'value_amount': 100.0,
                'nb_days': 0,
                'delay_type': 'days_after',
            })]

        lines = []
        percent_so_far = 0.0
        if first_payment > 0:
            if first_payment_type == 'fixed':
                first_pct = (
                    round((min(first_payment, line_amount) / line_amount) * 100.0, 6)
                    if line_amount
                    else 0.0
                )
            else:
                first_pct = first_payment
            if first_pct > 0:
                lines.append((0, 0, {
                    'value': 'percent',
                    'value_amount': first_pct,
                    'nb_days': 0,
                    'delay_type': 'days_after',
                }))
                percent_so_far = first_pct

        if installment_count < 1:
            return lines or [(0, 0, {
                'value': 'percent',
                'value_amount': 100.0,
                'nb_days': 0,
                'delay_type': 'days_after',
            })]

        days_map = {
            'monthly': 30,
            'weekly': 7,
            'daily': 1,
        }
        days_interval = days_map.get(term_values['installment_frequency'], 30)
        remaining_pct = max(100.0 - percent_so_far, 0.0)
        base_pct = round(remaining_pct / installment_count, 6) if installment_count else 0.0

        for index in range(installment_count):
            if index == installment_count - 1:
                value_amount = round(100.0 - percent_so_far, 6)
            else:
                value_amount = base_pct
                percent_so_far = round(percent_so_far + value_amount, 6)
            lines.append((0, 0, {
                'value': 'percent',
                'value_amount': value_amount,
                'nb_days': (index + 1) * days_interval,
                'delay_type': 'days_after',
            }))
        return lines
