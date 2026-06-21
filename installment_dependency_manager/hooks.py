# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    """
    Post-initialization hook to register installed modules.

    This automatically detects which installment modules are installed
    and registers their capabilities in the registry.

    Args:
        cr: Database cursor
        registry: Module registry
    """
    try:
        env = registry.env(cr)
        dep_registry = env['installment.dependency.registry']

        # Get list of installed modules
        installed_modules = env['ir.module.module'].search([
            ('state', '=', 'installed')
        ])
        module_names = {m.name for m in installed_modules}

        _logger.info("Registering installment module capabilities...")

        # Register payment_term_installment_extension
        if 'payment_term_installment_extension' in module_names:
            dep_registry.register(
                'payment_term_installment_extension',
                'payment_term_config'
            )
            _logger.info("Registered: payment_term_installment_extension -> payment_term_config")

        # Register invoice_installment_management
        if 'invoice_installment_management' in module_names:
            dep_registry.register(
                'invoice_installment_management',
                'installment_creation'
            )
            _logger.info("Registered: invoice_installment_management -> installment_creation")

        # Register installment_payment_extension
        if 'installment_payment_extension' in module_names:
            dep_registry.register(
                'installment_payment_extension',
                'installment_payment'
            )
            _logger.info("Registered: installment_payment_extension -> installment_payment")

        # Register installment_management_pro
        if 'installment_management_pro' in module_names:
            dep_registry.register(
                'installment_management_pro',
                'installment_analytics'
            )
            _logger.info("Registered: installment_management_pro -> installment_analytics")

        # Register account_invoice_installments
        if 'account_invoice_installments' in module_names:
            dep_registry.register(
                'account_invoice_installments',
                'order_type_classification'
            )
            _logger.info("Registered: account_invoice_installments -> order_type_classification")

        _logger.info("Installment module registration complete")

    except Exception as e:
        _logger.error(f"Error in post_init_hook: {str(e)}")
        raise
