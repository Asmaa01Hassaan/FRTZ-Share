# -*- coding: utf-8 -*-
from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class AccountMoveHook(models.Model):
    """
    Hook into existing account.move model.

    Calls coordinator when invoice posted, without modifying existing logic.
    """
    _inherit = 'account.move'

    def action_post(self):
        """
        Override action_post to notify coordinator after posting.

        IMPORTANT: This doesn't change any existing posting logic.
        It just notifies coordinator AFTER the invoice is posted.
        """
        # Call parent (existing logic - completely unchanged)
        result = super().action_post()

        # Notify coordinator AFTER posting (new code, doesn't modify existing logic)
        if self.move_type == 'out_invoice':
            try:
                coordinator = self.env['installment.coordinator']
                for move in self:
                    try:
                        status = coordinator.process_invoice_posted(move)
                        _logger.debug(f"Coordinator processed invoice: {status}")
                    except Exception as e:
                        # Log but don't fail posting if coordinator has issues
                        _logger.warning(f"Coordinator warning for invoice {move.name}: {str(e)}")
            except Exception as e:
                # If coordinator model doesn't exist, silently ignore
                _logger.debug(f"Coordinator not available: {str(e)}")

        return result
