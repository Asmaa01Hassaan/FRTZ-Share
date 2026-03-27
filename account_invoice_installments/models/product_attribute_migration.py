# -*- coding: utf-8 -*-
"""
Migration script to fix existing 'text' display_type values

This script migrates any product.attribute records that have display_type='text'
to display_type='radio' to fix frontend validation errors.
"""
from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)


def migrate_text_display_type(env):
    """
    Migrate any existing product.attribute records with display_type='text'
    to display_type='radio' (the default)
    
    This fixes the frontend error: "display_type' is not valid"
    """
    try:
        attributes = env['product.attribute'].search([('display_type', '=', 'text')])
        if attributes:
            count = len(attributes)
            attributes.write({'display_type': 'radio'})
            _logger.info(f"Migrated {count} product attribute(s) from 'text' to 'radio' display_type")
            return count
        return 0
    except Exception as e:
        _logger.error(f"Error migrating display_type: {e}")
        return 0


def post_init_hook(cr, registry):
    """Called after module installation/upgrade"""
    env = api.Environment(cr, SUPERUSER_ID, {})
    migrate_text_display_type(env)

