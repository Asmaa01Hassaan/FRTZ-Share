# -*- coding: utf-8 -*-
from odoo import models, api, fields, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class InstallmentCoordinator(models.Model):
    """
    High-level orchestrator for installment operations.

    Coordinates across multiple installment modules without modifying them.

    This is a "conductor" that knows:
    - What order to do things in
    - Which modules need to be involved
    - How to handle errors gracefully

    Usage by new/external code:
        coordinator = self.env['installment.coordinator']
        coordinator.process_invoice_posted(invoice)
        coordinator.process_payment_received(payment, installment, amount)
        coordinator.process_overdue_check()
    """
    _name = 'installment.coordinator'
    _description = 'Installment Coordinator'
    _singleton = True

    # Configuration
    auto_create_installments = fields.Boolean(
        default=True,
        help='Automatically create installments when invoice is posted'
    )
    auto_track_payments = fields.Boolean(
        default=True,
        help='Automatically track payments against installments'
    )
    auto_flag_overdue = fields.Boolean(
        default=True,
        help='Automatically flag overdue installments'
    )
    log_operations = fields.Boolean(
        default=True,
        help='Log all coordinator operations'
    )

    @api.model
    def process_invoice_posted(self, invoice):
        """
        Called when invoice is posted.

        Coordinates installment creation without modifying existing logic.

        Flow:
        1. Check if payment term has installments
        2. If yes, create installments via adapter
        3. Log the operation
        4. Return status

        Args:
            invoice (account.move): Posted invoice

        Returns:
            dict: Operation status with result details
        """
        adapter = self.env['installment.adapter.service']

        try:
            if not invoice:
                return {'status': 'error', 'reason': 'No invoice provided'}

            # Check if payment term exists
            if not invoice.invoice_payment_term_id:
                return {'status': 'skipped', 'reason': 'No payment term'}

            # Check if it's an installment term
            if not hasattr(invoice.invoice_payment_term_id, 'is_installment_term'):
                return {'status': 'skipped', 'reason': 'Payment term config not available'}

            if not invoice.invoice_payment_term_id.is_installment_term:
                return {'status': 'skipped', 'reason': 'Not an installment term'}

            if self.auto_create_installments:
                # Use adapter to create installments
                installments = adapter.create_installments(
                    invoice,
                    invoice.invoice_payment_term_id
                )

                if self.log_operations:
                    _logger.info(
                        f"Coordinator: Created {len(installments)} installments for invoice {invoice.name}"
                    )

                return {
                    'status': 'success',
                    'count': len(installments),
                    'installments': installments.ids if installments else [],
                }
            else:
                return {'status': 'skipped', 'reason': 'Auto-creation disabled'}

        except Exception as e:
            error_msg = f"Error processing invoice {invoice.name}: {str(e)}"
            _logger.error(error_msg)
            return {'status': 'error', 'message': error_msg}

    @api.model
    def process_payment_received(self, payment, installment, amount):
        """
        Called when payment is received against an installment.

        Coordinates payment recording without modifying existing modules.

        Args:
            payment (account.payment): Payment document
            installment (account.move.installment): Target installment
            amount (float): Payment amount

        Returns:
            dict: Operation status
        """
        adapter = self.env['installment.adapter.service']

        try:
            if not installment:
                return {'status': 'error', 'reason': 'No installment provided'}

            if amount <= 0:
                raise ValidationError(_("Payment amount must be positive"))

            if self.auto_track_payments:
                log = adapter.record_payment(installment, amount)

                if self.log_operations:
                    _logger.info(
                        f"Coordinator: Recorded payment of {amount} against installment {installment.id}"
                    )

                return {
                    'status': 'success',
                    'payment_log_id': log.id if log else None,
                }
            else:
                return {'status': 'skipped', 'reason': 'Auto-tracking disabled'}

        except Exception as e:
            error_msg = f"Error recording payment: {str(e)}"
            _logger.error(error_msg)
            return {'status': 'error', 'message': error_msg}

    @api.model
    def process_overdue_check(self):
        """
        Cron job: Check and flag overdue installments.

        Called by cron without touching existing module logic.

        Returns:
            dict: Operation status with found overdue installments
        """
        adapter = self.env['installment.adapter.service']

        try:
            if self.auto_flag_overdue:
                overdue = adapter.get_overdue_installments()

                if self.log_operations:
                    _logger.info(f"Coordinator: Found {len(overdue)} overdue installments")

                return {
                    'status': 'success',
                    'count': len(overdue),
                    'installments': overdue.ids if overdue else [],
                }
            else:
                return {'status': 'skipped', 'reason': 'Auto-flagging disabled'}

        except Exception as e:
            error_msg = f"Error in overdue check: {str(e)}"
            _logger.error(error_msg)
            return {'status': 'error', 'message': error_msg}

    @api.model
    def get_dependency_status(self):
        """
        Return which installment modules are installed.

        Helps debug dependency issues.

        Returns:
            dict: Status of each capability/module
        """
        adapter = self.env['installment.adapter.service']
        return adapter.get_module_status()

    @api.model
    def validate_dependencies(self):
        """
        Check that all required modules are installed.

        Returns:
            dict: Validation results with errors, warnings, and status
        """
        adapter = self.env['installment.adapter.service']

        result = adapter.validate_dependencies()

        if self.log_operations:
            if result['valid']:
                _logger.info("Coordinator: All dependencies valid")
            else:
                _logger.warning(f"Coordinator: Missing dependencies: {result['errors']}")

        return result

    @api.model
    def get_coordinator_status(self):
        """
        Get complete coordinator status and configuration.

        Returns:
            dict: Full status information
        """
        coordinator = self.browse(self.search([], limit=1))

        return {
            'name': 'Installment Coordinator',
            'version': '18.0.1.0.0',
            'configuration': {
                'auto_create_installments': coordinator.auto_create_installments,
                'auto_track_payments': coordinator.auto_track_payments,
                'auto_flag_overdue': coordinator.auto_flag_overdue,
                'log_operations': coordinator.log_operations,
            },
            'dependencies': self.validate_dependencies(),
            'module_status': self.get_dependency_status(),
        }

    def action_validate_dependencies(self):
        """Action button to validate dependencies"""
        result = self.validate_dependencies()

        message = "Dependencies Validation Result:\n\n"
        if result['valid']:
            message += "✓ All dependencies are valid!\n\n"
            message += "Available capabilities:\n"
            for cap, available in result['modules'].items():
                message += f"  • {cap}: {'✓' if available else '✗'}\n"
        else:
            message += "✗ Missing dependencies:\n"
            for error in result['errors']:
                message += f"  • {error}\n"

        if result['warnings']:
            message += "\nWarnings:\n"
            for warning in result['warnings']:
                message += f"  • {warning}\n"

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Dependencies Validation',
                'message': message,
                'sticky': False,
            }
        }

    def action_show_status(self):
        """Action button to show coordinator status"""
        status = self.get_coordinator_status()

        message = f"{status['name']} v{status['version']}\n\n"
        message += "Configuration:\n"
        for key, value in status['configuration'].items():
            message += f"  • {key}: {'Enabled' if value else 'Disabled'}\n"

        message += "\nModule Status:\n"
        for module, available in status['module_status'].items():
            message += f"  • {module}: {'✓' if available else '✗'}\n"

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Coordinator Status',
                'message': message,
                'sticky': True,
            }
        }
