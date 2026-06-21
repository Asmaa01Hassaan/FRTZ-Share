# -*- coding: utf-8 -*-
from odoo import models, api, fields, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class InstallmentAdapterService(models.Model):
    """
    Unified adapter/facade for installment operations.

    This wraps existing module functionality without changing it.

    IMPORTANT: This doesn't duplicate logic, just provides a clean interface.
    It calls existing models/methods from other modules.

    Usage:
        adapter = self.env['installment.adapter.service']
        adapter.create_installments(move, term)
        adapter.record_payment(installment, amount)
        adapter.get_overdue_installments()
    """
    _name = 'installment.adapter.service'
    _description = 'Installment Adapter Service'
    _singleton = True

    @api.model
    def create_installments(self, move, payment_term):
        """
        Create installments by delegating to existing module.

        This doesn't change any logic - just calls what's already there.

        Args:
            move (account.move): Invoice to create installments for
            payment_term (account.payment.term): Payment term with installment config

        Returns:
            list: Created installment records
        """
        try:
            if not move:
                raise ValidationError(_("Invoice is required"))

            if not payment_term:
                raise ValidationError(_("Payment term is required"))

            if not hasattr(payment_term, 'is_installment_term'):
                return []

            if not payment_term.is_installment_term:
                _logger.info(f"Payment term {payment_term.name} is not marked as installment term")
                return []

            # Trigger existing logic from invoice_installment_management
            # (which is already attached to account.move via _inherit)
            if hasattr(move, '_create_installments_from_payment_term'):
                move._create_installments_from_payment_term()

            # Get created installments
            installments = move.installment_ids if hasattr(move, 'installment_ids') else []

            _logger.info(f"Created {len(installments)} installments for invoice {move.name}")

            return installments

        except Exception as e:
            _logger.error(f"Error creating installments: {str(e)}")
            raise

    @api.model
    def record_payment(self, installment, amount, payment_method='bank_transfer'):
        """
        Record payment against installment.

        Wraps existing installment_payment_extension functionality.

        Args:
            installment (account.move.installment): Installment being paid
            amount (float): Amount being paid
            payment_method (str): Payment method code

        Returns:
            account.installment.payment.log: Created payment log record
        """
        try:
            if not installment:
                raise ValidationError(_("Installment is required"))

            if amount <= 0:
                raise ValidationError(_("Payment amount must be positive"))

            # Check if payment log model exists
            if not self.env.registry.get('account.installment.payment.log'):
                _logger.warning("account.installment.payment.log model not available")
                return None

            # Create payment log
            # NOTE: real model fields are `paid_amount` and `action_type`
            # (there is no `amount_paid`/`payment_method` on the log model).
            log = self.env['account.installment.payment.log'].create({
                'installment_id': installment.id,
                'paid_amount': amount,
                'action_type': payment_method,
            })

            _logger.info(f"Recorded payment of {amount} against installment {installment.id}")

            return log

        except Exception as e:
            _logger.error(f"Error recording payment: {str(e)}")
            raise

    @api.model
    def get_overdue_installments(self, days_threshold=0):
        """
        Get overdue installments from existing logic.

        Args:
            days_threshold (int): Days past due to consider overdue

        Returns:
            account.move.installment: Recordset of overdue installments
        """
        try:
            if not self.env.registry.get('account.move.installment'):
                _logger.warning("account.move.installment model not available")
                return self.env['account.move.installment']

            from datetime import timedelta
            today = fields.Date.today()
            overdue_date = today - timedelta(days=days_threshold)

            overdue = self.env['account.move.installment'].search([
                ('state', '!=', 'paid'),
                ('date_due', '<', overdue_date),
            ])

            _logger.debug(f"Found {len(overdue)} overdue installments")

            return overdue

        except Exception as e:
            _logger.error(f"Error getting overdue installments: {str(e)}")
            return self.env['account.move.installment']

    @api.model
    def reschedule_installment(self, installment, new_due_date, reason=''):
        """
        Reschedule installment to new due date.

        Wraps existing installment_management_pro functionality.

        Args:
            installment (account.move.installment): Installment to reschedule
            new_due_date (date): New due date
            reason (str): Reason for rescheduling

        Returns:
            bool: True if successful
        """
        try:
            if not installment:
                raise ValidationError(_("Installment is required"))

            if new_due_date <= fields.Date.today():
                raise ValidationError(_("New due date must be in the future"))

            old_date = installment.date_due
            installment.write({'date_due': new_due_date})

            # Create audit log if model exists.
            # NOTE: real model is `account.installment.reschedule.log` with
            # fields `old_date_due`/`new_date_due` and a required `change_type`.
            if self.env.registry.get('account.installment.reschedule.log'):
                self.env['account.installment.reschedule.log'].create({
                    'installment_id': installment.id,
                    'change_type': 'date_change',
                    'old_date_due': old_date,
                    'new_date_due': new_due_date,
                    'reason': reason,
                })

            _logger.info(f"Rescheduled installment {installment.id} from {old_date} to {new_due_date}")

            return True

        except Exception as e:
            _logger.error(f"Error rescheduling installment: {str(e)}")
            raise

    @api.model
    def get_installment_status(self, installment):
        """
        Get detailed status of an installment.

        Args:
            installment (account.move.installment): Installment to check

        Returns:
            dict: Status information
        """
        try:
            if not installment:
                raise ValidationError(_("Installment is required"))

            # Dict keys below are the adapter's public API contract; read them
            # from the real model fields (amount_total / amount_residual / date_due).
            amount_remaining = 0
            if hasattr(installment, 'amount_residual'):
                amount_remaining = installment.amount_residual

            return {
                'id': installment.id,
                'amount': installment.amount_total if hasattr(installment, 'amount_total') else 0,
                'amount_paid': installment.amount_paid if hasattr(installment, 'amount_paid') else 0,
                'amount_remaining': amount_remaining,
                'due_date': installment.date_due if hasattr(installment, 'date_due') else None,
                'state': installment.state if hasattr(installment, 'state') else 'unknown',
            }

        except Exception as e:
            _logger.error(f"Error getting installment status: {str(e)}")
            return {}

    @api.model
    def get_module_status(self):
        """
        Return status of all installment modules.

        Helps users understand which modules are installed and capabilities available.

        Returns:
            dict: Status of each capability
        """
        registry = self.env['installment.dependency.registry']

        modules_status = {
            'payment_term_config': registry.is_available('payment_term_config'),
            'installment_creation': registry.is_available('installment_creation'),
            'installment_payment': registry.is_available('installment_payment'),
            'installment_analytics': registry.is_available('installment_analytics'),
            'order_type_classification': registry.is_available('order_type_classification'),
        }

        _logger.debug(f"Module status: {modules_status}")

        return modules_status

    @api.model
    def validate_dependencies(self):
        """
        Check that all required modules are installed.

        Returns:
            dict: Validation results with errors and warnings
        """
        registry = self.env['installment.dependency.registry']
        status = self.get_module_status()

        errors = []
        warnings = []

        # Check required dependencies
        if not status['payment_term_config']:
            errors.append("payment_term_installment_extension not installed")

        if not status['installment_creation']:
            errors.append("invoice_installment_management not installed")

        # Optional dependencies
        if not status['installment_payment']:
            warnings.append("installment_payment_extension not installed (optional)")

        if not status['installment_analytics']:
            warnings.append("installment_management_pro not installed (optional)")

        result = {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'modules': status,
        }

        _logger.info(f"Dependency validation: {result}")

        return result

    def action_validate_dependencies(self):
        """UI button: validate dependencies and show the result as a notification.

        Thin wrapper around `validate_dependencies()` (no business logic here).
        """
        result = self.validate_dependencies()
        if result['valid']:
            message = _("All required installment modules are installed.")
            msg_type = 'success'
        else:
            message = _("Missing required modules: %s") % ", ".join(result['errors'])
            msg_type = 'warning'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Dependency Validation"),
                'message': message,
                'type': msg_type,
                'sticky': False,
            },
        }

    def action_show_module_status(self):
        """UI button: show which installment capabilities are available.

        Thin wrapper around `get_module_status()` (no business logic here).
        """
        status = self.get_module_status()
        lines = [
            "%s: %s" % (key, _("available") if available else _("not installed"))
            for key, available in status.items()
        ]
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Installment Module Status"),
                'message': "\n".join(lines),
                'type': 'info',
                'sticky': False,
            },
        }
