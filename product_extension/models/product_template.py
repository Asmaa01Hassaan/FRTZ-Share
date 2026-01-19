# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    code = fields.Char(
        string="Code",
        help="Product code identifier"
    )

    subscription_ok = fields.Boolean(
        string='Subscription',
        default=True,
        help="Can be used in subscription orders"
    )

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
        index=True
    )
    internal_reference_new = fields.Char(
        string="Internal Reference"
    )
    cost_method = fields.Selection(
        related='categ_id.property_cost_method',
        readonly=True
    )

    def write(self, vals):
        """Override write to auto-generate reference when category changes to automatic"""
        # Check if category is being changed
        if 'categ_id' in vals and not vals.get('internal_reference_new'):
            category = self.env['product.category'].browse(vals['categ_id'])
            if category.reference_type == 'automatic':
                # Generate reference for records that don't have one
                for product in self:
                    if not product.internal_reference_new:
                        generated_ref = self._generate_automatic_reference(category)
                        if generated_ref:
                            product.internal_reference_new = generated_ref
        
        return super().write(vals)

    def _generate_automatic_reference(self, category):
        """Generate automatic reference based on category configuration"""
        # Get sequence from category or use default
        sequence = category.reference_sequence_id
        if not sequence:
            # Use default sequence
            sequence = self.env.ref(
                'product_extension.seq_product_reference_default',
                raise_if_not_found=False
            )
        
        if not sequence:
            return False
        
        # Generate reference using sequence
        generated_ref = sequence.next_by_id()
        if not generated_ref:
            return False
        
        # Apply validation rules if set (for formatting)
        if category.validate_length and category.reference_length:
            # Pad or truncate to required length
            if category.validate_type and category.reference_char_type == 'number':
                # Ensure numeric and pad with zeros
                try:
                    num = int(''.join(filter(str.isdigit, generated_ref)) or '0')
                    generated_ref = str(num).zfill(category.reference_length)
                except:
                    generated_ref = generated_ref[:category.reference_length].zfill(category.reference_length)
            else:
                # Mixed: truncate or pad
                generated_ref = generated_ref[:category.reference_length].ljust(
                    category.reference_length, '0'
                )
        
        return generated_ref

    @api.model
    def create(self, vals_list):
        """Override create to auto-generate internal reference when category is set to automatic"""
        # Handle both single dict and list of dicts
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        
        for vals in vals_list:
            # Generate reference if category is set to automatic and reference is not provided
            if not vals.get('internal_reference_new'):
                categ_id = vals.get('categ_id')
                if categ_id:
                    category = self.env['product.category'].browse(categ_id)
                    if category.reference_type == 'automatic':
                        generated_ref = self._generate_automatic_reference(category)
                        if generated_ref:
                            vals['internal_reference_new'] = generated_ref
        
        return super().create(vals_list)

    @api.constrains('type', 'categ_id')
    def _check_product_type_in_category(self):
        """Validate that product type is allowed in the selected category"""
        for product in self:
            if not product.categ_id:
                continue  # No category, allow any type
            
            category = product.categ_id
            
            # Check if any restrictions are set (any boolean is True)
            has_restrictions = category.allow_consu or category.allow_service or category.allow_combo
            
            if not has_restrictions:
                continue  # No restrictions set, allow any type
            
            # Check if the product type is allowed based on boolean fields
            type_allowed = False
            if product.type == 'consu' and category.allow_consu:
                type_allowed = True
            elif product.type == 'service' and category.allow_service:
                type_allowed = True
            elif product.type == 'combo' and category.allow_combo:
                type_allowed = True
            
            if not type_allowed:
                type_labels = {
                    'consu': 'Goods',
                    'service': 'Service',
                    'combo': 'Combo'
                }
                current_label = type_labels.get(product.type, product.type)
                
                # Build list of allowed types
                allowed_labels = []
                if category.allow_consu:
                    allowed_labels.append('Goods')
                if category.allow_service:
                    allowed_labels.append('Service')
                if category.allow_combo:
                    allowed_labels.append('Combo')
                
                raise ValidationError(
                    _("Product type '%(current)s' is not allowed in category '%(category)s'. "
                      "Allowed types: %(allowed)s") % {
                        'current': current_label,
                        'category': category.name,
                        'allowed': ', '.join(allowed_labels)
                    }
                )

    @api.constrains('internal_reference_new', 'categ_id')
    def _check_internal_reference_new(self):
        """Enhanced validation for internal reference based on category rules"""
        for product in self:
            cat = product.categ_id
            ref = product.internal_reference_new or ''

            # Skip validation if no category or manual mode
            if not cat or cat.reference_type == 'manual':
                continue
            
            # Skip validation if automatic (system generates, should be valid)
            if cat.reference_type == 'automatic':
                # Just ensure it's not empty (should be generated)
                if not ref:
                    raise ValidationError(
                        _("Internal Reference should be automatically generated for category '%s'. "
                          "Please save the product again or check the sequence configuration.") % cat.name
                    )
                continue
            
            # Validation mode: enforce rules
            if cat.reference_type == 'validation':
                # Check if reference is provided (required when validation is enabled)
                if not ref:
                    raise ValidationError(
                        _("Internal Reference is required for category '%s'.") % cat.name
                    )
                
                # Length validation (if enabled)
                if cat.validate_length:
                    if not cat.reference_length:
                        continue  # No length set, skip length validation
                    if len(ref) != cat.reference_length:  # Fixed: use != instead of >
                        raise ValidationError(
                            _("Internal Reference must be exactly %(length)d characters for category '%(category)s'. "
                              "Current length: %(current)d") % {
                                'length': cat.reference_length,
                                'category': cat.name,
                                'current': len(ref)
                            }
                        )
                
                # Type validation (if enabled)
                if cat.validate_type:
                    if cat.reference_char_type == 'number':
                        if not ref.isdigit():
                            raise ValidationError(
                                _("Internal Reference must contain numbers only for category '%s'.") % cat.name
                            )
                    elif cat.reference_char_type == 'mix':
                        # Enhanced mix validation: must contain both letters and numbers
                        has_letter = any(c.isalpha() for c in ref)
                        has_digit = any(c.isdigit() for c in ref)
                        if not (has_letter and has_digit):
                            raise ValidationError(
                                _("Internal Reference must contain both letters and numbers for category '%s'.") % cat.name
                            )

    @api.depends('name', 'internal_reference_new')
    def _compute_display_name(self):
        """Compute display name as 'INTERNAL_REFERENCE NAME' format"""
        for product in self:
            name = product.name or ''
            if product.internal_reference_new:
                name = f"{product.internal_reference_new} {name}"
            product.display_name = name

    def name_get(self):
        """Override to return formatted display name"""
        result = []
        for product in self:
            result.append((product.id, product.display_name or product.name))
        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """
        Override name_search to include internal_reference_new in search
        Allows searching by both name and internal reference
        """
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('internal_reference_new', operator, name)]
        records = self.search(domain + args, limit=limit)
        return records.name_get()
