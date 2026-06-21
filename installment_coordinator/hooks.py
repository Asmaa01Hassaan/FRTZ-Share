# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    """
    Post-initialization hook to set up coordinator.

    Args:
        cr: Database cursor
        registry: Module registry
    """
    try:
        env = registry.env(cr)

        # Get or create singleton coordinator
        coordinator = env['installment.coordinator'].search([], limit=1)
        if not coordinator:
            coordinator = env['installment.coordinator'].create({
                'auto_create_installments': True,
                'auto_track_payments': True,
                'auto_flag_overdue': True,
                'log_operations': True,
            })
            _logger.info("Created Installment Coordinator singleton")
        else:
            _logger.info("Installment Coordinator already exists")

        # Validate dependencies
        result = coordinator.validate_dependencies()
        if result['valid']:
            _logger.info("Coordinator: All dependencies validated successfully")
        else:
            _logger.warning(f"Coordinator: Missing dependencies - {result['errors']}")

    except Exception as e:
        _logger.error(f"Error in post_init_hook: {str(e)}")
        # Don't raise - let installation continue even if coordinator setup fails
