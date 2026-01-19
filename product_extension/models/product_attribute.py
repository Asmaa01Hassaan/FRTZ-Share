# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'
    
    allow_free_text = fields.Boolean(
        string="Display Type Test",
        default=False,
        help="Enable this to allow users to enter custom text values for this attribute. "
             "This will automatically set Display Type to 'Pills', Variant Creation to 'Never', "
             "and create a free text attribute value. The attribute will display as pills in the UI."
    )
    
    def read(self, fields=None, load='_classic_read'):
        """Ensure display_type is never 'text' when reading"""
        result = super().read(fields, load)
        for record in result:
            if record.get('display_type') == 'text':
                record['display_type'] = 'pills'
                # Also fix it in the database
                self.browse(record['id']).write({'display_type': 'pills', 'allow_free_text': True})
        return result
    
    @api.onchange('allow_free_text')
    def _onchange_allow_free_text(self):
        """Handle free text option changes - use pills display type"""
        if self.allow_free_text:
            # Automatically set display type to pills (for UI compatibility)
            self.display_type = 'pills'
            # Automatically set variant creation to never
            self.create_variant = 'no_variant'
            # Ensure a free text attribute value with space exists (using One2many)
            self._ensure_text_attribute_value_onchange()
        else:
            # When disabling free text, disable is_custom on all values
            # But keep the free text value (with space name) so we can reuse it when rechecking
            if self.value_ids:
                for val in self.value_ids:
                    val.is_custom = False
    
    def _ensure_text_attribute_value_onchange(self):
        """Ensure there's an attribute value with is_custom=True and name=' ' for text type (onchange)"""
        if self.allow_free_text:
            # Check if there's already a value with space name (regardless of is_custom)
            # This handles the case when unchecking and rechecking
            text_value = self.value_ids.filtered(lambda v: v.name.strip() == '' or v.name == ' ')
            if not text_value:
                # No existing value with space - add new value using One2many field (works in onchange)
                # For onchange, we need to preserve existing values
                # Build commands list with existing values and new one
                commands = []
                # Include all existing value_ids (both saved and unsaved)
                for val in self.value_ids:
                    if val.id:
                        # Link existing saved record
                        commands.append((4, val.id))
                    else:
                        # For unsaved records in onchange, recreate them
                        # Get all field values to preserve them
                        val_dict = {'is_custom': val.is_custom}
                        if hasattr(val, 'name') and val.name:
                            val_dict['name'] = val.name
                        commands.append((0, 0, val_dict))
                # Add the new free text value with space
                commands.append((0, 0, {
                    'name': ' ',
                    'is_custom': True,
                }))
                if commands:
                    self.value_ids = commands
            else:
                # Reuse existing value - ensure it has is_custom=True and name is space
                for val in text_value:
                    val.is_custom = True
                    if val.name != ' ':
                        val.name = ' '
    
    def _ensure_text_attribute_value(self):
        """Ensure there's an attribute value with is_custom=True and name=' ' for text type (after save)"""
        if self.allow_free_text and self.id:
            # Check if there's already a value with space name (regardless of is_custom)
            # This handles the case when unchecking and rechecking - reuse existing value
            text_value = self.value_ids.filtered(lambda v: v.name.strip() == '' or v.name == ' ')
            if not text_value:
                # No existing value with space - create a new attribute value with space
                self.env['product.attribute.value'].create({
                    'name': ' ',
                    'attribute_id': self.id,
                    'is_custom': True,
                })
            else:
                # Reuse existing value - ensure it has is_custom=True and name is space
                # Only update if needed to avoid unnecessary writes
                for val in text_value:
                    if not val.is_custom or val.name != ' ':
                        val.write({
                            'is_custom': True,
                            'name': ' ',
                        })
    
    @api.model
    def create(self, vals):
        """Set display_type to pills and create_variant to no_variant when free text is enabled"""
        # Ensure display_type is never 'text'
        if vals.get('display_type') == 'text':
            vals['display_type'] = 'pills'
            vals['allow_free_text'] = True
        
        if vals.get('allow_free_text'):
            vals['display_type'] = 'pills'
            vals['create_variant'] = 'no_variant'
        
        record = super().create(vals)
        
        if record.allow_free_text:
            record._ensure_text_attribute_value()
            # Enable is_custom on all existing values
            record.value_ids.write({'is_custom': True})
        
        return record
    
    def write(self, vals):
        """Handle free text option changes"""
        # Fix any invalid display_type='text' to 'pills'
        if 'display_type' in vals and vals['display_type'] == 'text':
            vals['display_type'] = 'pills'
            vals['allow_free_text'] = True
        
        # Also check existing records for invalid display_type
        for record in self:
            if record.display_type == 'text':
                vals['display_type'] = 'pills'
                if 'allow_free_text' not in vals:
                    vals['allow_free_text'] = True
        
        # Handle free text option changes
        if 'allow_free_text' in vals:
            if vals['allow_free_text']:
                # When enabling free text, set display_type to pills and create_variant to no_variant
                vals['display_type'] = 'pills'
                vals['create_variant'] = 'no_variant'
                # Enable is_custom on all values
                if self.value_ids:
                    self.value_ids.write({'is_custom': True})
            else:
                # When disabling free text, disable is_custom on all values
                if self.value_ids:
                    self.value_ids.write({'is_custom': False})
        
        result = super().write(vals)
        
        # Ensure text attribute value exists after write
        if 'allow_free_text' in vals and vals['allow_free_text']:
            self._ensure_text_attribute_value()
        
        # Also handle when new values are added to an attribute with free text enabled
        if 'value_ids' in vals and self.allow_free_text:
            self.value_ids.write({'is_custom': True})
        
        return result
    
    @api.model
    def _fix_invalid_display_types(self):
        """Fix any existing records with display_type='text' and convert to 'pills'"""
        invalid_attrs = self.search([('display_type', '=', 'text')])
        if invalid_attrs:
            invalid_attrs.write({
                'display_type': 'pills',
                'allow_free_text': True,
                'create_variant': 'no_variant',
            })
            # Ensure free text values exist
            for attr in invalid_attrs:
                attr._ensure_text_attribute_value()


class ProductAttributeValue(models.Model):
    _inherit = 'product.attribute.value'
    
    name = fields.Char(
        string="Value",
        required=True,
        translate=True,
        help="For free text attributes, a space is allowed as a valid value."
    )
    
    def _is_free_text_value(self):
        """Check if this is a free text attribute value"""
        return self.is_custom or (self.attribute_id and self.attribute_id.allow_free_text)
    
    @api.model
    def create(self, vals):
        """Automatically set is_custom if the attribute allows free text and allow space as name"""
        # Check if attribute allows free text
        attribute = None
        if vals.get('attribute_id'):
            attribute = self.env['product.attribute'].browse(vals.get('attribute_id'))
        
        # Allow space as name if is_custom is True or attribute allows free text
        is_free_text = vals.get('is_custom') or (attribute and attribute.allow_free_text)
        
        # For free text values, preserve space if provided, or set to space if empty
        # Also replace "." with space as a shortcut
        if is_free_text:
            if 'name' in vals:
                # Replace "." with space as a shortcut
                if vals['name'] == '.':
                    vals['name'] = ' '
                # If name is empty string or None, set to space
                elif not vals['name'] or (vals['name'] and not vals['name'].strip() and vals['name'] != ' '):
                    vals['name'] = ' '
            else:
                # If name not provided, set to space
                vals['name'] = ' '
        
        record = super().create(vals)
        if record.attribute_id and record.attribute_id.allow_free_text:
            record.is_custom = True
            # Ensure name is at least a space if it's empty
            if not record.name or (record.name and not record.name.strip() and record.name != ' '):
                record.name = ' '
        return record
    
    def write(self, vals):
        """Allow space as name when is_custom is True or attribute allows free text"""
        # Check if this is a free text value before write
        is_free_text_before = any(record._is_free_text_value() for record in self)
        
        # If enabling is_custom, mark as free text
        if 'is_custom' in vals and vals['is_custom']:
            is_free_text_before = True
        
        # Check if attribute_id is being set and it allows free text
        if 'attribute_id' in vals:
            attribute = self.env['product.attribute'].browse(vals['attribute_id'])
            if attribute.allow_free_text:
                is_free_text_before = True
        
        # If name is being updated for a free text value
        if is_free_text_before and 'name' in vals:
            # Handle space preservation for free text attributes
            # Replace "." with space as a shortcut
            name_value = vals.get('name')
            if name_value == '.':
                vals['name'] = ' '
            elif name_value is None:
                vals['name'] = ' '
            elif name_value == '':
                # Empty string - convert to space for free text
                vals['name'] = ' '
            elif name_value.strip() == '' and name_value != ' ':
                # Only whitespace (but not a single space) - convert to space
                vals['name'] = ' '
            # If it's already a single space ' ', keep it
            # If it has content, keep it as is
        
        result = super().write(vals)
        
        # After write, ensure free text values have at least a space
        # This handles cases where the value becomes free text after write
        for record in self:
            if record._is_free_text_value():
                # If name is empty or only whitespace (but not a single space), set to space
                if not record.name or (record.name and not record.name.strip() and record.name != ' '):
                    record.name = ' '
        
        return result
    
    @api.constrains('name')
    def _check_name_required(self):
        """Override to allow space as valid name for free text values"""
        for record in self:
            # For free text values, space is a valid name
            if record._is_free_text_value():
                # If name is empty or only whitespace (but not a single space), set to space
                if not record.name or (record.name and not record.name.strip() and record.name != ' '):
                    # Use sudo to bypass any restrictions when setting the space
                    record.sudo().write({'name': ' '})
                # Space is valid for free text, so skip validation - don't raise error
                return
            # For non-free text values, ensure name is not empty (required=True handles this)
            if not record.name or not record.name.strip():
                raise ValidationError(_("The attribute value name cannot be empty."))