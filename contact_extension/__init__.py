from . import models
from . import controllers

# Apply patch for KeyError: 'params' fix
def _apply_dataset_patch():
    """Apply patch to DataSet controller"""
    try:
        # Try enterprise web module first
        try:
            from odooenter.odoo.addons.web.controllers import dataset as web_dataset
        except ImportError:
            # Fallback to standard web module
            from odoo.addons.web.controllers import dataset as web_dataset
        
        # Import our patched function
        from .controllers.dataset import _patched_call_kw_readonly
        
        # Apply the patch
        web_dataset.DataSet._call_kw_readonly = _patched_call_kw_readonly
        
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info("Successfully patched DataSet._call_kw_readonly to fix KeyError: 'params'")
    except Exception as e:
        import logging
        _logger = logging.getLogger(__name__)
        _logger.warning("Failed to patch DataSet._call_kw_readonly: %s", str(e))

# Apply patch when module is imported
_apply_dataset_patch()
