# -*- coding: utf-8 -*-
"""
Fix for KeyError: 'params' in _call_kw_readonly
This patch makes the readonly check more defensive by handling cases
where the JSON data might not have the expected structure.

This is a workaround for Odoo 18 issue where _call_kw_readonly is called
during routing evaluation before JSON data is fully parsed.
"""

import logging
from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


def _patched_call_kw_readonly(self):
    """
    Safely determine if a method should be readonly.
    Handles cases where JSON data might not be fully parsed or structured.
    """
    try:
        json_data = request.get_json_data()
        # Check if 'params' key exists in the JSON data
        if not isinstance(json_data, dict) or 'params' not in json_data:
            # If params don't exist, default to False (not readonly)
            _logger.debug("JSON data missing 'params' key, defaulting to readonly=False")
            return False
        
        params = json_data['params']
        
        # Validate params structure
        if not isinstance(params, dict):
            _logger.debug("Params is not a dict, defaulting to readonly=False")
            return False
        
        # Check if model and method are present
        if 'model' not in params or 'method' not in params:
            _logger.debug("Params missing 'model' or 'method', defaulting to readonly=False")
            return False
        
        try:
            model_class = request.registry[params['model']]
        except KeyError as e:
            _logger.debug("Model %s not found in registry", params['model'])
            raise NotFound() from e
        
        method_name = params['method']
        
        # Check if method has _readonly attribute
        for cls in model_class.mro():
            method = getattr(cls, method_name, None)
            if method is not None and hasattr(method, '_readonly'):
                return method._readonly
        
        return False
        
    except (ValueError, AttributeError, TypeError) as e:
        # Handle cases where JSON parsing fails or request structure is unexpected
        _logger.debug("Error in _call_kw_readonly: %s, defaulting to readonly=False", str(e))
        return False
    except Exception as e:
        # Log unexpected errors but don't break the request
        _logger.warning("Unexpected error in _call_kw_readonly: %s, defaulting to readonly=False", str(e))
        return False


# Patch the DataSet controller when this module is loaded
def _patch_dataset_controller():
    """Patch the DataSet._call_kw_readonly method to handle missing params"""
    try:
        # Try to import from enterprise web module first
        try:
            from odooenter.odoo.addons.web.controllers import dataset as web_dataset
        except ImportError:
            # Fallback to standard web module
            from odoo.addons.web.controllers import dataset as web_dataset
        
        # Replace the method with our patched version
        web_dataset.DataSet._call_kw_readonly = _patched_call_kw_readonly
        _logger.info("Successfully patched DataSet._call_kw_readonly to fix KeyError: 'params'")
    except Exception as e:
        _logger.warning("Failed to patch DataSet._call_kw_readonly: %s", str(e))


# Don't apply patch here - use post_init_hook instead
# The patch will be applied via post_init_hook in hooks.py

