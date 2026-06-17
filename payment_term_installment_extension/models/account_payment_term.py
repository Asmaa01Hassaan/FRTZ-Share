# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from odoo.tools import float_compare, format_date, formatLang

class AccountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'
    
    is_installment_term = fields.Boolean(
        string=_("Auto JE"),
        default=True,
        help=_("Indicates if this payment term is for installments")
    )
    
    installment_count = fields.Integer(
        string=_("Installments Num."),
        default=0,
        help=_("Number of installments for this payment term")
    )
    
    first_payment_type = fields.Selection([
        ('percent', 'Percent'),
        ('fixed', 'Fixed'),
    ], string=_("First Payment Type"), default='fixed',
        help=_("Type of first payment: percent or fixed amount"))
    
    first_payment_percentage = fields.Float(
        string=_("First Payment"),
        default=0.0,
        digits=(16, 2),
        help=_("first payment")
    )
    
    show_installment_scope = fields.Boolean(compute='_compute_installment_config_visibility')
    readonly_installment_scope = fields.Boolean(compute='_compute_installment_config_visibility')
    show_installment_baseline_date = fields.Boolean(compute='_compute_installment_config_visibility')
    readonly_installment_baseline_date = fields.Boolean(compute='_compute_installment_config_visibility')

    scope = fields.Selection([
        ('per_invoice', 'Per Invoice'),
        ('per_lines', 'Per Lines'),
    ], string=_("Scope"),
        default=lambda self: self.env['installment.config.mixin']._get_installment_default_scope(),
        help=_("Scope of payment term application"))
    
    settlement_trigger = fields.Selection([
        ('cia', 'CIA-Cash in Advance'),
        ('cod', 'Cash on Delivery'),
        ('cbd', 'Cash Before Delivery'),
    ], string=_("Payment Timing"), default='cia',
        help=_("Settlement trigger type"))
    
    baseline_date = fields.Selection([
        ('invoice_date', 'Invoice Date'),
        ('posting_date', 'Posting Date'),
        ('receipt_date', 'Receipt Date'),
    ], string=_("Baseline Date"),
        default=lambda self: self.env['installment.config.mixin']._get_installment_default_baseline_date(),
        help=_("Baseline date for payment term calculation"))
    
    pay_type = fields.Selection([
        ('spot', 'Spot(Full)'),
        ('fixed', 'Fixed(Auto)'),
        ('custom', 'Custom(Manual)'),
    ], string=_("Payment Plan"), default='spot',
        help=_("Type of payment plan"))
    grace_period = fields.Integer(string=_("GracePeriod (days)"))

    installment_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('weekly', 'Weekly'),
        ('daily', 'Daily'),
    ], string=_("Installment Frequency"), default='monthly',
        help=_("Frequency of installments"))
    
    apply_remming_to = fields.Selection([
        ('first_installment', 'First Installment'),
        ('last_installment', 'Last Installment'),
    ], string=_("Apply Remaining To"), default='last_installment',
        help=_("Apply remaining amount to which installment"))
    
    method = fields.Selection([
        ('sd', 'SD-Saladuction'),
        ('sdd', 'Salary Deduction Duble'),
    ], string=_("Method"), default='sd',
        help=_("Payment method"))

    def _compute_installment_config_visibility(self):
        states = self.env['installment.config.mixin']._get_installment_field_ui_states()
        for term in self:
            term.show_installment_scope = states['show_installment_scope']
            term.readonly_installment_scope = states['readonly_installment_scope']
            term.show_installment_baseline_date = states['show_installment_baseline_date']
            term.readonly_installment_baseline_date = states['readonly_installment_baseline_date']

    @api.model
    def default_get(self, fields_list):
        return self.env['installment.config.mixin']._apply_installment_config_defaults(
            fields_list,
            super().default_get(fields_list),
        )
    
    def _generate_auto_name(self):
        """
        Generate automatic name based on payment term settings in Arabic format:
        [نوع الدفع] | الدفعة الأولى: [الدفعة الأولى]% | تاريخ الأساس: [تاريخ الأساس] | فترة السماح: [فترة السماح] يوم
        
        Rules:
        - If pay_type = 'fixed': use "installment_count أقساط منتظمة"
        - If pay_type = 'custom': use "[عدد line_ids] أقساط مجدولة"
        - If pay_type = 'spot': use "دفع فوري"
        - Only add parts that have values (skip 0 or empty values)
        """
        # Get pay type label in Arabic
        # CRITICAL: Put installment count in square brackets BEFORE "أقساط منتظمة" or "أقساط مجدولة"
        # Format: [number] أقساط منتظمة
        if self.pay_type == 'fixed':
            # Ensure installment_count is read correctly
            installment_count = self.installment_count or 0
            if installment_count > 0:
                # Format: [number] أقساط منتظمة
                # pay_type_label = f"  أقساط منتظمة[{int(installment_count)}] "
                pay_type_label = f"  عدد {int(installment_count)} أقساط منتظمة "
            else:
                pay_type_label = "أقساط منتظمة"
        elif self.pay_type == 'custom':
            line_count = len(self.line_ids) if self.line_ids else 0
            if line_count > 0:
                # Format: [number] أقساط مجدولة
                pay_type_label = f" عدد {line_count} أقساط مجدولة "
            else:
                pay_type_label = "أقساط مجدولة"
        elif self.pay_type == 'spot':
            pay_type_label = "دفع فوري"
        else:
            pay_type_label = "دفع"
        
        # Build name parts - First Payment comes first, then pay_type_label
        name_parts = []

        # First Payment - only add if value exists and > 0 (appears first)
        if self.first_payment_percentage and self.first_payment_percentage > 0:
            first_pay = f"{self.first_payment_percentage:.0f}" if self.first_payment_percentage == int(self.first_payment_percentage) else f"{self.first_payment_percentage:.2f}"
            # Add % sign only if first_payment_type is 'percent'
            if self.first_payment_type == 'percent':
                name_parts.append(f"د.أ. {first_pay}%")
            else:
                name_parts.append(f"د.أ. {first_pay}")
        
        # Add pay_type_label after first payment
        name_parts.append(pay_type_label)
        
        # Baseline Date - only add if value exists
        if self.baseline_date:
            baseline_labels = {
                'invoice_date': 'تاريخ الفاتورة',
                'posting_date': 'تاريخ الإثبات',
                'receipt_date': 'تاريخ الاستلام',
            }
            baseline_label = baseline_labels.get(self.baseline_date, self.baseline_date)
            name_parts.append(f"تستحق من  {baseline_label}")
        
        # Grace Period - only add if value exists and > 0
        if self.grace_period and self.grace_period > 0:
            name_parts.append(f"فترة السماح: {self.grace_period} يوم")
        
        # Early Discount - only add if exists and has value
        if hasattr(self, 'early_discount') and self.early_discount:
            if hasattr(self, 'discount_percentage') and self.discount_percentage and self.discount_percentage > 0:
                discount = f"{self.discount_percentage:.0f}" if self.discount_percentage == int(self.discount_percentage) else f"{self.discount_percentage:.2f}"
                name_parts.append(f"الخصم المبكر: {discount}%")
        
        # Join all parts with " | "
        return " | ".join(name_parts)
    
    @api.onchange('pay_type', 'installment_frequency', 'installment_count', 'apply_remming_to', 
                  'first_payment_type', 'first_payment_percentage', 'baseline_date', 'grace_period', 
                  'line_ids', 'early_discount', 'discount_percentage')
    def _onchange_auto_name(self):
        """Automatically update name based on payment term settings"""
        # Always update name when any relevant field changes
        self.name = self._generate_auto_name()
    
    @api.onchange('pay_type', 'installment_frequency', 'installment_count', 'apply_remming_to', 'first_payment_type', 'first_payment_percentage')
    def _onchange_fixed_installment(self):
        """
        Automatically generate/update line_ids when pay_type is 'fixed' and installment data is provided.
        Uses the clean _regenerate_line_ids method.
        """
        self._regenerate_line_ids()
        # Update name after regenerating lines
        self.name = self._generate_auto_name()
    
    def _regenerate_line_ids(self):
        """
        Clean method to regenerate line_ids based on rules:
        1. If first_payment_percentage != 0: Edit the first row only
        2. If pay_type = 'fixed' and installment_count != 0: 
           - Add/edit other rows based on installment_count
           - If first_payment_percentage != 0: Generate installment_count lines (in addition to first payment line)
           - If first_payment_percentage == 0: Generate installment_count lines
        3. Ensure total percentage = 100%
        """
        lines_to_update = []
        existing_lines = list(self.line_ids) if self.line_ids else []
        existing_lines_count = len(existing_lines)
        
        has_first_payment = self.first_payment_percentage and self.first_payment_percentage > 0
        
        # CRITICAL: If we need to reduce the number of lines (installment_count reduced),
        # we must delete all existing lines first, then recreate them
        # This ensures that unsaved lines are also deleted
        need_full_rebuild = False
        if self.pay_type == 'fixed' and self.installment_count > 0:
            if has_first_payment:
                total_lines_needed = 1 + self.installment_count
            else:
                total_lines_needed = self.installment_count
            
            # If we have more lines than needed, we need to rebuild
            if existing_lines_count > total_lines_needed:
                need_full_rebuild = True
        
        # If we need to rebuild, delete all lines first
        if need_full_rebuild:
            # Delete all existing lines (both saved and unsaved)
            for line in existing_lines:
                if line.id:
                    lines_to_update.append((2, line.id))
            # Note: Unsaved lines will be removed when we set self.line_ids
        
        # Step 1: Create/edit the first row if first_payment_percentage != 0
        if has_first_payment:
            first_line_data = {
                'value': self.first_payment_type,
                'value_amount': self.first_payment_percentage,
                'nb_days': 0,
                'delay_type': 'days_after',
            }
            
            # If we're rebuilding, always create new line
            # Otherwise, edit existing first line if it exists
            if need_full_rebuild:
                # Create new line (all lines were deleted)
                lines_to_update.append((0, 0, first_line_data))
            elif existing_lines_count > 0:
                first_line = existing_lines[0]
                if first_line.id:
                    lines_to_update.append((1, first_line.id, first_line_data))
                else:
                    # Unsaved line, update directly
                    first_line.value = first_line_data['value']
                    first_line.value_amount = first_line_data['value_amount']
                    first_line.nb_days = first_line_data['nb_days']
                    first_line.delay_type = first_line_data['delay_type']
            else:
                # No existing lines, create first line
                lines_to_update.append((0, 0, first_line_data))
        
        # Step 2: Handle installment lines if pay_type = 'fixed'
        if self.pay_type == 'fixed' and self.installment_count > 0:
            days_map = {'monthly': 30, 'weekly': 7, 'daily': 1}
            days_interval = days_map.get(self.installment_frequency, 30)
            
            # Calculate number of installment lines needed
            if has_first_payment:
                num_installment_lines = self.installment_count
                if self.first_payment_type == 'percent':
                    remaining_percentage = 100.0 - self.first_payment_percentage
                else:
                    remaining_percentage = 100.0
                start_index = 1  # Start from second line (first is first_payment)
            else:
                # No first_payment: use all installment_count lines
                # IMPORTANT: The first line (default 100% created by Odoo) will be edited to be the first installment
                # We start from index 0 to edit this default line
                num_installment_lines = self.installment_count
                remaining_percentage = 100.0
                start_index = 0  # Start from first line (edit the default 100% line)
            
            if num_installment_lines > 0:
                # CRITICAL: Round base_percentage first to ensure consistency
                # This prevents floating-point precision issues
                base_percentage = round(remaining_percentage / num_installment_lines, 2)
                
                # Calculate total number of lines needed
                # If has_first_payment: 1 first payment line + num_installment_lines
                # If no first_payment: num_installment_lines total
                if has_first_payment:
                    total_lines_needed = 1 + num_installment_lines
                else:
                    total_lines_needed = num_installment_lines
                
                # Delete extra existing lines (from the end)
                # CRITICAL: This ensures that when installment_count is reduced, extra lines are deleted
                # Note: If need_full_rebuild is True, we already deleted all lines, so skip this
                if not need_full_rebuild and existing_lines_count > total_lines_needed:
                    # Delete extra lines from the end
                    # We need to delete both saved lines (with id) and unsaved lines (without id)
                    lines_to_delete = []
                    for i in range(total_lines_needed, existing_lines_count):
                        if existing_lines[i].id:
                            # Saved line: use (2, id) to delete
                            lines_to_delete.append((2, existing_lines[i].id))
                        # For unsaved lines (without id), they will be automatically removed
                        # when we set self.line_ids = lines_to_update, as they won't be included
                        # in the update
                    
                    # Add delete commands to lines_to_update
                    lines_to_update.extend(lines_to_delete)
                
                # Calculate value_amount for all installment lines
                # For the last line, calculate exact percentage to ensure total = 100%
                # Note: If no first_payment, all lines are installments (first_payment_pct = 0)
                if has_first_payment and self.first_payment_type == 'percent':
                    first_payment_pct = self.first_payment_percentage
                else:
                    first_payment_pct = 0  # No first payment or first payment is fixed
                
                # Calculate total percentage so far (first payment + all installments except last)
                # Use rounded base_percentage to ensure consistency
                total_percentage_so_far = first_payment_pct + (base_percentage * (num_installment_lines - 1))
                
                # Calculate last installment percentage to ensure total = 100% exactly
                # CRITICAL: Use round() to avoid floating-point precision issues
                last_percent_value = round(100.0 - total_percentage_so_far, 2)
                
                # Double-check: If last_percent_value is too small or negative, recalculate
                if last_percent_value < 0.01:
                    # Recalculate with adjusted base_percentage
                    # Reduce base_percentage slightly to ensure last_percent_value is positive
                    adjusted_base = round((remaining_percentage - 0.01) / num_installment_lines, 2)
                    total_percentage_so_far = first_payment_pct + (adjusted_base * (num_installment_lines - 1))
                    last_percent_value = round(100.0 - total_percentage_so_far, 2)
                    base_percentage = adjusted_base
                
                # Ensure last_percent_value is not negative and not zero
                if last_percent_value <= 0:
                    # If last_percent_value is negative or zero, recalculate base_percentage
                    # This can happen if first_payment_percentage is too large or installment_count is too small
                    # Solution: Recalculate to ensure all installments are distributed evenly
                    if num_installment_lines > 1:
                        # Recalculate base_percentage to ensure last_percent_value is positive
                        adjusted_remaining = remaining_percentage - 0.01  # Leave small margin for last line
                        base_percentage = adjusted_remaining / num_installment_lines
                        total_percentage_so_far = first_payment_pct + (base_percentage * (num_installment_lines - 1))
                        last_percent_value = round(100.0 - total_percentage_so_far, 2)
                    else:
                        # Only one installment line, use remaining_percentage directly
                        last_percent_value = round(remaining_percentage, 2)
                
                # Final validation: Ensure last_percent_value is positive
                if last_percent_value <= 0:
                    last_percent_value = round(base_percentage, 2)  # Use base_percentage as fallback
                
                # Add/edit installment lines
                # Use a set to track which line IDs we've already updated (avoid duplicates)
                updated_line_ids = set()
                
                for i in range(int(num_installment_lines)):
                    days = (i + 1) * days_interval
                    line_index = start_index + i
                    
                    # Use last_percent_value for the last line, base_percentage for others
                    # base_percentage is already rounded, so use it directly
                    if i == num_installment_lines - 1:
                        value_amount = last_percent_value
                    else:
                        value_amount = base_percentage  # Already rounded
                    
                    # Ensure value_amount is not zero (critical check)
                    if value_amount <= 0:
                        value_amount = base_percentage  # Already rounded
                    
                    # Edit existing line or create new one
                    # If we're rebuilding, always create new lines
                    if need_full_rebuild:
                        # Create new line (all lines were deleted)
                        lines_to_update.append((0, 0, {
                            'value': 'percent',
                            'value_amount': value_amount,
                            'nb_days': days,
                            'delay_type': 'days_after',
                        }))
                    elif line_index < existing_lines_count:
                        existing_line = existing_lines[line_index]
                        # CRITICAL: Always update existing line, even if it has value = 0
                        # This ensures:
                        # 1. The first row (default 100%) is edited when first_payment_percentage = 0
                        # 2. The second row (or any row) with 0 value is fixed
                        # 3. All rows are updated correctly
                        if existing_line.id:
                            # Check if we've already added an update for this line (avoid duplicates)
                            if existing_line.id not in updated_line_ids:
                                lines_to_update.append((1, existing_line.id, {
                                    'value': 'percent',
                                    'value_amount': value_amount,  # This will fix value = 0
                                    'nb_days': days,
                                    'delay_type': 'days_after',
                                }))
                                updated_line_ids.add(existing_line.id)
                        else:
                            # Unsaved line (in onchange), update directly
                            # This is critical to fix value = 0 for unsaved lines
                            # Note: Unsaved lines that are updated directly will be preserved
                            # when we set self.line_ids = lines_to_update
                            # Extra unsaved lines (not updated) will be automatically removed
                            existing_line.value = 'percent'
                            existing_line.value_amount = value_amount  # Fix value = 0
                            existing_line.nb_days = days
                            existing_line.delay_type = 'days_after'
                    else:
                        # Create new line (only if we need more lines)
                        lines_to_update.append((0, 0, {
                            'value': 'percent',
                            'value_amount': value_amount,
                            'nb_days': days,
                            'delay_type': 'days_after',
                        }))
        
        # Step 3: If no first_payment and pay_type is not 'fixed', ensure at least one line with 100%
        elif not has_first_payment and self.pay_type != 'fixed':
            if existing_lines_count > 0:
                if existing_lines[0].id:
                    lines_to_update.append((1, existing_lines[0].id, {
                        'value': 'percent',
                        'value_amount': 100.0,
                        'nb_days': 0,
                        'delay_type': 'days_after',
                    }))
                else:
                    existing_lines[0].value = 'percent'
                    existing_lines[0].value_amount = 100.0
                    existing_lines[0].nb_days = 0
                    existing_lines[0].delay_type = 'days_after'
            else:
                lines_to_update.append((0, 0, {
                    'value': 'percent',
                    'value_amount': 100.0,
                    'nb_days': 0,
                    'delay_type': 'days_after',
                }))
        
        # Apply updates
        if lines_to_update:
            # CRITICAL: When we set self.line_ids, Odoo will:
            # 1. Apply all commands in lines_to_update (create, update, delete)
            # 2. Remove any unsaved lines that are not included in lines_to_update
            # This ensures that when installment_count is reduced, extra unsaved lines are deleted
            self.line_ids = lines_to_update

        # Safety guard for Odoo core constraint:
        # Payment terms must always contain at least one percent line with total = 100.
        # This edge case happens when first_payment_type is fixed and no fixed-installment
        # percent schedule is generated (non-fixed plan, or fixed plan with zero installments).
        if (
            self.line_ids
            and has_first_payment
            and self.first_payment_type == 'fixed'
            and not (self.pay_type == 'fixed' and self.installment_count > 0)
        ):
            percent_lines = self.line_ids.filtered(lambda line: line.value == 'percent')
            if not percent_lines:
                self.line_ids = [(0, 0, {
                    'value': 'percent',
                    'value_amount': 100.0,
                    'nb_days': 0,
                    'delay_type': 'days_after',
                })]
        
        # Final validation: Ensure total percentage = 100% exactly
        # This is critical to fix any rounding errors or calculation issues
        if self.line_ids and self.pay_type == 'fixed' and self.installment_count > 0:
            # Calculate total of all percent lines
            percent_lines = [line for line in self.line_ids if line.value == 'percent']
            if percent_lines:
                total_percent = sum(line.value_amount for line in percent_lines)
                
                # If total is not exactly 100%, adjust the last percent line
                if abs(total_percent - 100.0) > 0.01:
                    # Calculate adjustment needed
                    adjustment = 100.0 - total_percent
                    
                    # Apply adjustment to the last percent line
                    last_percent_line = percent_lines[-1]
                    new_value = round(last_percent_line.value_amount + adjustment, 2)
                    
                    # Ensure new_value is positive
                    if new_value <= 0:
                        # If adjustment makes value negative, redistribute
                        # This should rarely happen, but we handle it
                        new_value = 0.01
                    
                    # Update the last line
                    if last_percent_line.id:
                        self.line_ids = [(1, last_percent_line.id, {
                            'value': 'percent',
                            'value_amount': new_value,
                            'nb_days': last_percent_line.nb_days,
                            'delay_type': last_percent_line.delay_type,
                        })]
                    else:
                        # Unsaved line, update directly
                        last_percent_line.value_amount = new_value
        
        # Final verification: Ensure all lines are correct and total = 100%
        # This is a safety check to fix any remaining issues, especially 0% values
        if self.line_ids and self.pay_type == 'fixed' and self.installment_count > 0:
            has_first_payment = self.first_payment_percentage and self.first_payment_percentage > 0
            start_index = 1 if has_first_payment else 0
            
            days_map = {'monthly': 30, 'weekly': 7, 'daily': 1}
            days_interval = days_map.get(self.installment_frequency, 30)
            
            if has_first_payment:
                num_installment_lines = self.installment_count
                if self.first_payment_type == 'percent':
                    remaining_percentage = 100.0 - self.first_payment_percentage
                else:
                    remaining_percentage = 100.0
            else:
                num_installment_lines = self.installment_count
                remaining_percentage = 100.0
            
            if num_installment_lines > 0:
                # CRITICAL: Round base_percentage first to ensure consistency
                base_percentage = round(remaining_percentage / num_installment_lines, 2)
                
                # Calculate last_percent_value
                if has_first_payment and self.first_payment_type == 'percent':
                    first_payment_pct = self.first_payment_percentage
                else:
                    first_payment_pct = 0
                
                # Use rounded base_percentage for consistency
                total_percentage_so_far = first_payment_pct + (base_percentage * (num_installment_lines - 1))
                last_percent_value = round(100.0 - total_percentage_so_far, 2)
                
                if last_percent_value <= 0:
                    last_percent_value = base_percentage  # Already rounded
                
                # Verify and fix any lines with incorrect values (especially 0% values)
                verification_updates = []
                for i, line in enumerate(self.line_ids):
                    if i >= start_index and i < start_index + num_installment_lines:
                        line_num = i - start_index
                        expected_days = (line_num + 1) * days_interval
                        
                        if line_num == num_installment_lines - 1:
                            expected_value = last_percent_value
                        else:
                            expected_value = base_percentage
                        
                        # Check if line needs fixing (especially if value = 0)
                        needs_fix = False
                        if line.value != 'percent':
                            needs_fix = True
                        elif line.value_amount == 0:  # CRITICAL: Fix 0% values
                            needs_fix = True
                        elif abs(line.value_amount - expected_value) > 0.01:
                            needs_fix = True
                        elif line.nb_days != expected_days:
                            needs_fix = True
                        
                        if needs_fix and line.id:
                            verification_updates.append((1, line.id, {
                                'value': 'percent',
                                'value_amount': expected_value,
                                'nb_days': expected_days,
                                'delay_type': 'days_after',
                            }))
                        elif needs_fix and not line.id:
                            # Unsaved line, update directly
                            line.value = 'percent'
                            line.value_amount = expected_value
                            line.nb_days = expected_days
                            line.delay_type = 'days_after'
                
                # Apply verification updates if any
                if verification_updates:
                    self.line_ids = verification_updates
    
    def action_update_lines(self):
        """
        Update line_ids to ensure:
        1. At least one percent line exists
        2. Sum of all percent lines = 100%
        Uses simple math: last_percent_line = 100% - sum(other_percent_lines)
        """
        for record in self:
            lines_to_update = []
            existing_lines = list(record.line_ids) if record.line_ids else []
            
            if not existing_lines:
                # No lines exist, create a default 100% line
                lines_to_update.append((0, 0, {
                    'value': 'percent',
                    'value_amount': 100.0,
                    'nb_days': 0,
                    'delay_type': 'days_after',
                }))
            else:
                # Calculate total of all percent lines
                percent_lines = [line for line in existing_lines if line.value == 'percent']
                total_percent = sum(line.value_amount for line in percent_lines)
                
                if not percent_lines:
                    # No percent lines exist, convert first line to percent with 100%
                    first_line = existing_lines[0]
                    if first_line.id:
                        lines_to_update.append((1, first_line.id, {
                            'value': 'percent',
                            'value_amount': 100.0,
                            'nb_days': first_line.nb_days or 0,
                            'delay_type': first_line.delay_type or 'days_after',
                        }))
                    else:
                        # Unsaved line, update directly
                        first_line.value = 'percent'
                        first_line.value_amount = 100.0
                        if not first_line.nb_days:
                            first_line.nb_days = 0
                        if not first_line.delay_type:
                            first_line.delay_type = 'days_after'
                elif abs(total_percent - 100.0) > 0.01:
                    # Total is not 100%, adjust the last percent line
                    # Calculate: last_percent_line = 100% - sum(other_percent_lines)
                    if len(percent_lines) > 1:
                        # Multiple percent lines: adjust the last one
                        other_percent_total = sum(line.value_amount for line in percent_lines[:-1])
                        last_percent_value = 100.0 - other_percent_total
                        
                        # Ensure last_percent_value is not negative
                        if last_percent_value < 0:
                            last_percent_value = 0
                        
                        last_percent_line = percent_lines[-1]
                        if last_percent_line.id:
                            lines_to_update.append((1, last_percent_line.id, {
                                'value': 'percent',
                                'value_amount': last_percent_value,
                                'nb_days': last_percent_line.nb_days or 0,
                                'delay_type': last_percent_line.delay_type or 'days_after',
                            }))
                        else:
                            # Unsaved line, update directly
                            last_percent_line.value_amount = last_percent_value
                    else:
                        # Only one percent line: set it to 100%
                        if percent_lines[0].id:
                            lines_to_update.append((1, percent_lines[0].id, {
                                'value': 'percent',
                                'value_amount': 100.0,
                                'nb_days': percent_lines[0].nb_days or 0,
                                'delay_type': percent_lines[0].delay_type or 'days_after',
                            }))
                        else:
                            # Unsaved line, update directly
                            percent_lines[0].value_amount = 100.0
            
            # Apply updates
            if lines_to_update:
                record.line_ids = lines_to_update
            
            # Verify the update worked
            record.invalidate_recordset(['line_ids'])
            
            # Clear cache to refresh views
            self.env.registry.clear_cache()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Payment term lines have been updated. Total = 100% (using simple math: 100% - sum of other lines).'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_reload_lines(self):
        """
        Reload and regenerate line_ids to ensure:
        - Total percentage = 100%
        - No line has value = 0
        """
        for record in self:
            record._regenerate_line_ids()
            # Clear cache to refresh views
            self.env.registry.clear_cache()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Payment term lines have been reloaded and validated. Total = 100% and no zero values.'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_reset_lines(self):
        """
        Reset line_ids by:
        1. Setting installment_count = 0
        2. Setting first_payment_percentage = 0
        3. Deleting all existing lines and creating a default 100% line in one operation
        """
        for record in self:
            # Prepare lines_to_update: delete all and create default line in one command
            lines_to_update = []
            
            # Delete all existing lines
            if record.line_ids:
                for line in record.line_ids:
                    if line.id:
                        lines_to_update.append((2, line.id))
            
            # Create default 100% line (in the same command to avoid validation error)
            lines_to_update.append((0, 0, {
                'value': 'percent',
                'value_amount': 100.0,
                'nb_days': 0,
                'delay_type': 'days_after',
            }))
            
            # First, update line_ids to ensure we always have at least one 100% line
            # This must be done before updating other fields to avoid validation error
            record.line_ids = lines_to_update
            
            # Then update other fields using super().write() to bypass _regenerate_line_ids()
            # We use context to skip regeneration since we already set the lines
            record.with_context(skip_regenerate=True).write({
                'installment_count': 0,
                'first_payment_percentage': 0.0,
            })
            
            # Clear cache to refresh views
            self.env.registry.clear_cache()
        
        # Return action to reload the page
        # The page will reload automatically, showing the updated data
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    
    def write(self, vals):
        """
        Override write to regenerate line_ids when important fields are updated.
        """
        result = super().write(vals)
        
        # Auto-generate/update line_ids for fixed payment type
        # Skip regeneration if context has skip_regenerate flag (used by action_reset_lines)
        if not self.env.context.get('skip_regenerate'):
            if any(field in vals for field in ['pay_type', 'installment_frequency', 'installment_count', 'first_payment_type', 'first_payment_percentage']):
                for record in self:
                    record._regenerate_line_ids()
        
        # Auto-update name if relevant fields are updated
        name_fields = ['pay_type', 'installment_count', 'first_payment_percentage', 'baseline_date', 
                       'grace_period', 'early_discount', 'discount_percentage', 'line_ids']
        if any(field in vals for field in name_fields):
            for record in self:
                # Only update name if at least one relevant field has a value
                if record.pay_type or record.first_payment_percentage or record.baseline_date or record.grace_period:
                    record.name = record._generate_auto_name()
        
        # Clear caches when installment-related fields are updated
        # This ensures views and computed fields are refreshed immediately
        installment_fields = [
            'is_installment_term',
            'installment_count',
            'first_payment_type',
            'first_payment_percentage',
            'scope',
            'settlement_trigger',
            'baseline_date',
            'pay_type',
            'installment_frequency',
            'apply_remming_to',
            'method',
        ]
        
        if any(field in vals for field in installment_fields):
            # Clear cache to refresh views and computed fields
            # Note: In Odoo 18, use clear_cache() instead of clear_caches()
            self.env.registry.clear_cache()
        
        return result

    def _get_term_line_amount(self, term_line, total, currency, company, date_ref):
        if not total:
            return 0.0
        if term_line.value == 'percent':
            return currency.round(total * (term_line.value_amount / 100.0))
        if term_line.value == 'fixed':
            return currency.round(company.currency_id._convert(
                term_line.value_amount,
                currency,
                company,
                date_ref,
            ))
        return 0.0

    def _get_header_first_payment_amount(self, total, currency):
        self.ensure_one()
        if not total:
            return 0.0
        if self.first_payment_type == 'fixed':
            return min(self.first_payment_percentage or 0.0, total)
        pct = self.first_payment_percentage or 0.0
        return currency.round(total * (pct / 100.0))

    def _get_fallback_installment_amount(self, total, first_pay, currency):
        self.ensure_one()
        count = self.installment_count or 0
        if not total or count < 1:
            return 0.0
        if self.first_payment_type == 'percent':
            remaining_pct = max(0.0, 100.0 - (self.first_payment_percentage or 0.0))
            return currency.round(total * (remaining_pct / count) / 100.0)
        remaining = max(0.0, total - first_pay)
        return currency.round(remaining / count)

    def get_line_payment_amount_breakdown(self, total, currency=None, company=None, date_ref=None):
        """Return due amount and first installment amount for a line total."""
        self.ensure_one()
        currency = currency or self.env.company.currency_id
        company = company or self.env.company
        date_ref = date_ref or fields.Date.today()
        zero = {'due_amount': 0.0, 'first_installment_amount': 0.0}

        if not total or float_compare(total, 0.0, precision_digits=2) == 0:
            return zero

        if self.line_ids:
            term_lines = self.line_ids.sorted(key=lambda line: (line.nb_days, line.id))
            line_amounts = [
                self._get_term_line_amount(term_line, total, currency, company, date_ref)
                for term_line in term_lines
            ]
            down_payment_indices = [
                index for index, term_line in enumerate(term_lines) if term_line.nb_days == 0
            ]
            installment_indices = [
                index for index, term_line in enumerate(term_lines) if term_line.nb_days > 0
            ]

            if down_payment_indices:
                first_pay = sum(line_amounts[index] for index in down_payment_indices)
                first_installment_amount = (
                    line_amounts[installment_indices[0]] if installment_indices else 0.0
                )
            elif self.first_payment_percentage and self.first_payment_percentage > 0:
                first_pay = self._get_header_first_payment_amount(total, currency)
                first_installment_amount = line_amounts[0] if line_amounts else 0.0
            else:
                first_pay = 0.0
                first_installment_amount = line_amounts[0] if line_amounts else 0.0

            return {
                'due_amount': total - first_pay,
                'first_installment_amount': first_installment_amount,
            }

        first_pay = self._get_header_first_payment_amount(total, currency)
        return {
            'due_amount': total - first_pay,
            'first_installment_amount': self._get_fallback_installment_amount(total, first_pay, currency),
        }

    def _render_installment_preview_line(self, sequence, amount, due_date, currency):
        return (
            "<div>"
            + _(
                "<b>%(count)s#</b> Installment of <b>%(amount)s</b> due on "
                "<b style='color: #704A66;'>%(date)s</b>",
                count=sequence,
                amount=formatLang(self.env, amount, currency_obj=currency),
                date=format_date(self.env, due_date),
            )
            + "</div>"
        )

    def _set_example_preview_discount(self):
        self.ensure_one()
        self.example_preview_discount = ""
        if not self.early_discount:
            return
        date = self._get_last_discount_date_formatted(
            self.example_date or fields.Date.context_today(self)
        )
        discount_amount = self._get_amount_due_after_discount(self.example_amount, 0.0)
        self.example_preview_discount = _(
            "Early Payment Discount: <b>%(amount)s</b> if paid before <b>%(date)s</b>",
            amount=formatLang(self.env, discount_amount, currency_obj=self.currency_id),
            date=date,
        )

    def _get_preview_due_date(self, date_ref, nb_days, delay_type='days_after'):
        preview_line = self.env['account.payment.term.line'].new({
            'nb_days': nb_days,
            'delay_type': delay_type,
        })
        return preview_line._get_due_date(date_ref)

    def _build_fixed_preview_schedule(self):
        """Build a virtual fixed-plan schedule for preview (does not persist line_ids)."""
        self.ensure_one()
        schedule = []
        has_first_payment = self.first_payment_percentage and self.first_payment_percentage > 0
        if has_first_payment:
            schedule.append({
                'nb_days': 0,
                'delay_type': 'days_after',
                'value': self.first_payment_type,
                'value_amount': self.first_payment_percentage,
            })

        installment_count = self.installment_count or 0
        if installment_count < 1:
            return schedule

        days_map = {'monthly': 30, 'weekly': 7, 'daily': 1}
        days_interval = days_map.get(self.installment_frequency, 30)
        if has_first_payment:
            if self.first_payment_type == 'percent':
                remaining_percentage = 100.0 - self.first_payment_percentage
            else:
                remaining_percentage = 100.0
        else:
            remaining_percentage = 100.0

        base_percentage = round(remaining_percentage / installment_count, 2)
        first_payment_pct = (
            self.first_payment_percentage
            if has_first_payment and self.first_payment_type == 'percent'
            else 0.0
        )
        total_percentage_so_far = first_payment_pct + (base_percentage * (installment_count - 1))
        last_percent_value = round(100.0 - total_percentage_so_far, 2)
        if last_percent_value <= 0:
            last_percent_value = base_percentage

        for index in range(installment_count):
            schedule.append({
                'nb_days': (index + 1) * days_interval,
                'delay_type': 'days_after',
                'value': 'percent',
                'value_amount': last_percent_value if index == installment_count - 1 else base_percentage,
            })
        return schedule

    def _get_installment_preview_entries(self, date_ref, currency, company):
        """Return installment preview rows as [{'due_date', 'amount'}] without touching journal logic."""
        self.ensure_one()
        amount = self.example_amount or 0.0
        if float_compare(amount, 0.0, precision_digits=2) == 0:
            return []

        if self.pay_type == 'fixed' and not self.line_ids:
            schedule = self._build_fixed_preview_schedule()
        elif not self.line_ids:
            return []
        else:
            schedule = [
                {
                    'nb_days': line.nb_days,
                    'delay_type': line.delay_type,
                    'value': line.value,
                    'value_amount': line.value_amount,
                    'date_calculation_type': line.date_calculation_type,
                    'fixed_due_date': line.fixed_due_date,
                    '_line': line,
                }
                for line in self.line_ids
            ]

        entries = []
        for item in schedule:
            term_line = item.get('_line')
            if term_line:
                due_date = term_line._get_due_date(date_ref)
                line_amount = self._get_term_line_amount(term_line, amount, currency, company, date_ref)
            else:
                due_date = self._get_preview_due_date(date_ref, item['nb_days'], item.get('delay_type', 'days_after'))
                preview_line = self.env['account.payment.term.line'].new({
                    'value': item['value'],
                    'value_amount': item['value_amount'],
                    'nb_days': item['nb_days'],
                    'delay_type': item.get('delay_type', 'days_after'),
                })
                line_amount = self._get_term_line_amount(preview_line, amount, currency, company, date_ref)

            if item['value'] not in ('percent', 'fixed'):
                continue
            entries.append({'due_date': due_date, 'amount': line_amount})

        entries.sort(key=lambda entry: entry['due_date'])
        if entries:
            total_preview = sum(entry['amount'] for entry in entries)
            difference = amount - total_preview
            if float_compare(abs(difference), 0.01, precision_digits=2) > 0:
                entries[-1]['amount'] = currency.round(entries[-1]['amount'] + difference)
        return entries

    def _compute_installment_example_preview(self):
        """Preview-only installment display; journal posting still uses _compute_terms."""
        self.ensure_one()
        currency = self.currency_id
        date_ref = self.example_date or fields.Date.context_today(self)
        company = self.company_id or self.env.company
        self._set_example_preview_discount()

        example_preview = ""
        if self.pay_type == 'spot':
            if self.line_ids:
                terms = super()._compute_terms(
                    date_ref=date_ref,
                    currency=currency,
                    company=company,
                    tax_amount=0,
                    tax_amount_currency=0,
                    untaxed_amount=self.example_amount,
                    untaxed_amount_currency=self.example_amount,
                    sign=1,
                )
                for index, info_by_dates in enumerate(self._get_amount_by_date(terms).values()):
                    example_preview += (
                        "<div>"
                        + _(
                            "<b>%(count)s#</b> Installment of <b>%(amount)s</b> due on "
                            "<b style='color: #704A66;'>%(date)s</b>",
                            count=index + 1,
                            amount=formatLang(
                                self.env, info_by_dates['amount'], currency_obj=currency
                            ),
                            date=info_by_dates['date'],
                        )
                        + "</div>"
                    )
        elif self.pay_type in ('fixed', 'custom'):
            for index, entry in enumerate(
                self._get_installment_preview_entries(date_ref, currency, company),
                start=1,
            ):
                example_preview += self._render_installment_preview_line(
                    index, entry['amount'], entry['due_date'], currency
                )

        self.example_preview = example_preview

    @api.depends(
        'currency_id',
        'example_amount',
        'example_date',
        'line_ids.value',
        'line_ids.value_amount',
        'line_ids.nb_days',
        'line_ids.delay_type',
        'line_ids.date_calculation_type',
        'line_ids.fixed_due_date',
        'early_discount',
        'discount_percentage',
        'discount_days',
        'is_installment_term',
        'pay_type',
        'first_payment_type',
        'first_payment_percentage',
        'installment_count',
        'installment_frequency',
    )
    def _compute_example_preview(self):
        standard_terms = self.filtered(lambda term: not term.is_installment_term)
        installment_terms = self - standard_terms
        if standard_terms:
            super(AccountPaymentTerm, standard_terms)._compute_example_preview()
        for term in installment_terms:
            term._compute_installment_example_preview()
    
    def _compute_terms(self, date_ref, currency, company, tax_amount, tax_amount_currency, sign, untaxed_amount, untaxed_amount_currency, cash_rounding=None):
        """
        Override _compute_terms to return a single journal entry line when is_installment_term = True.
        
        When is_installment_term is True, instead of creating multiple journal entry lines
        (one for each payment term line), we create a single line with the total amount,
        similar to a standard 100% payment term.
        """
        # If is_installment_term is False, use the standard behavior
        if not self.is_installment_term:
            return super()._compute_terms(
                date_ref, currency, company, tax_amount, tax_amount_currency, 
                sign, untaxed_amount, untaxed_amount_currency, cash_rounding
            )
        
        # When is_installment_term is True, return a single line with total amount
        self.ensure_one()
        company_currency = company.currency_id
        total_amount = tax_amount + untaxed_amount
        total_amount_currency = tax_amount_currency + untaxed_amount_currency
        
        # Calculate the first due date from the first payment term line
        # This will be used as the due date for the single journal entry line
        first_due_date = date_ref
        if self.line_ids:
            first_line = self.line_ids[0]
            first_due_date = first_line._get_due_date(date_ref)
        
        pay_term = {
            'total_amount': total_amount,
            'discount_percentage': self.discount_percentage if self.early_discount else 0.0,
            'discount_date': date_ref + relativedelta(days=(self.discount_days or 0)) if self.early_discount else False,
            'discount_balance': 0,
            'line_ids': [],
        }
        
        # Handle early discount if applicable
        if self.early_discount:
            discount_percentage = self.discount_percentage / 100.0
            if self.early_pay_discount_computation in ('excluded', 'mixed'):
                pay_term['discount_balance'] = company_currency.round(total_amount - untaxed_amount * discount_percentage)
                pay_term['discount_amount_currency'] = currency.round(total_amount_currency - untaxed_amount_currency * discount_percentage)
            else:
                pay_term['discount_balance'] = company_currency.round(total_amount * (1 - discount_percentage))
                pay_term['discount_amount_currency'] = currency.round(total_amount_currency * (1 - discount_percentage))
            
            if cash_rounding:
                cash_rounding_difference_currency = cash_rounding.compute_difference(currency, pay_term['discount_amount_currency'])
                if not currency.is_zero(cash_rounding_difference_currency):
                    pay_term['discount_amount_currency'] += cash_rounding_difference_currency
                    rate = abs(total_amount_currency / total_amount) if total_amount else 0.0
                    pay_term['discount_balance'] = company_currency.round(pay_term['discount_amount_currency'] / rate) if rate else 0.0
        
        # Create a single line with the total amount
        # Use the first due date from the payment term lines
        pay_term['line_ids'].append({
            'date': first_due_date,
            'company_amount': total_amount,
            'foreign_amount': total_amount_currency,
        })
        
        return pay_term
    
    @api.model
    def create(self, vals):
        """
        Override create to auto-generate line_ids for fixed payment type and clear caches.
        
        Note: clear_caches() is used here to ensure views are refreshed immediately
        after creating a payment term with installment fields.
        
        ⚠️ WARNING: This may impact performance in production environments.
        Consider removing or making it conditional based on environment.
        """
        # Auto-generate line_ids for fixed payment type
        lines = []
        first_payment_type = vals.get('first_payment_type', 'fixed')
        first_payment_percentage = vals.get('first_payment_percentage', 0.0)
        pay_type = vals.get('pay_type')
        installment_count = vals.get('installment_count', 0)
        has_first_payment = first_payment_percentage and first_payment_percentage > 0
        
        # Step 1: Add first payment line if first_payment_percentage > 0
        if has_first_payment:
            lines.append((0, 0, {
                'value': first_payment_type,  # 'percent' or 'fixed'
                'value_amount': first_payment_percentage,
                'nb_days': 0,
                'delay_type': 'days_after',
            }))
            
            # If first_payment is percent and not 100%, and pay_type is not 'fixed',
            # we need to add remaining percentage to complete 100%
            if (first_payment_type == 'percent' and 
                first_payment_percentage < 100.0 and 
                pay_type != 'fixed'):
                # Add remaining percentage line
                remaining_percentage = 100.0 - first_payment_percentage
                lines.append((0, 0, {
                    'value': 'percent',
                    'value_amount': remaining_percentage,
                    'nb_days': 0,
                    'delay_type': 'days_after',
                }))
            # Odoo requires at least one percent line with total percent = 100.
            # If first payment is a fixed amount and no fixed-installment schedule is generated,
            # add a default 100% percent line to satisfy core payment term constraints.
            elif first_payment_type == 'fixed' and (pay_type != 'fixed' or installment_count < 1):
                lines.append((0, 0, {
                    'value': 'percent',
                    'value_amount': 100.0,
                    'nb_days': 0,
                    'delay_type': 'days_after',
                }))
        
        # If no first_payment and pay_type is not 'fixed', ensure at least one line with 100%
        elif not has_first_payment and pay_type != 'fixed':
            # Create a default 100% line
            lines.append((0, 0, {
                'value': 'percent',
                'value_amount': 100.0,
                'nb_days': 0,
                'delay_type': 'days_after',
            }))
        
        # Step 2: Add installment lines if pay_type = 'fixed'
        if pay_type == 'fixed' and installment_count > 0:
            installment_frequency = vals.get('installment_frequency', 'monthly')
            
            # Calculate days based on frequency
            days_map = {
                'monthly': 30,
                'weekly': 7,
                'daily': 1,
            }
            days_interval = days_map.get(installment_frequency, 30)
            
            # Calculate number of installment lines needed
            if has_first_payment:
                num_installment_lines = installment_count
                if first_payment_type == 'percent':
                    remaining_percentage = 100.0 - first_payment_percentage
                else:
                    remaining_percentage = 100.0
            else:
                num_installment_lines = installment_count
                remaining_percentage = 100.0
            
            # Calculate base percentage per installment line
            if num_installment_lines > 0:
                base_percentage = remaining_percentage / num_installment_lines
                
                # Generate installment lines
                for i in range(int(num_installment_lines)):
                    days = (i + 1) * days_interval  # Start from days_interval (not 0)
                    
                    # For the last line, calculate exact percentage to ensure total = 100%
                    if i == num_installment_lines - 1:
                        # Calculate total percentage of all lines except last installment line
                        if has_first_payment:
                            if first_payment_type == 'percent':
                                first_payment_pct = first_payment_percentage
                            else:
                                first_payment_pct = 0  # Fixed amount doesn't count in percentage
                        else:
                            first_payment_pct = 0
                        
                        # Calculate what we have so far (first payment + all installment lines except last)
                        total_percentage_so_far = first_payment_pct + (base_percentage * (num_installment_lines - 1))
                        value_amount = 100.0 - total_percentage_so_far
                        
                        # Ensure value_amount is not negative
                        if value_amount < 0:
                            value_amount = 0
                    else:
                        value_amount = base_percentage
                    
                    lines.append((0, 0, {
                        'value': 'percent',
                        'value_amount': value_amount,
                        'nb_days': days,
                        'delay_type': 'days_after',
                    }))
        
        # Add line_ids to vals if not already set
        if lines and 'line_ids' not in vals:
            vals['line_ids'] = lines
        
        result = super().create(vals)
        
        # Auto-update name if relevant fields are set
        name_fields = ['pay_type', 'installment_count', 'first_payment_percentage', 'baseline_date', 
                       'grace_period', 'early_discount', 'discount_percentage']
        if any(field in vals for field in name_fields):
            for record in result:
                # Only update name if at least one relevant field has a value
                if record.pay_type or record.first_payment_percentage or record.baseline_date or record.grace_period:
                    record.name = record._generate_auto_name()
        
        # Clear caches when creating payment term with installment fields
        installment_fields = [
            'is_installment_term',
            'installment_count',
            'first_payment_percentage',
        ]
        
        if any(field in vals for field in installment_fields):
            # Clear cache to refresh views and computed fields
            # Note: In Odoo 18, use clear_cache() instead of clear_caches()
            self.env.registry.clear_cache()
        
        return result

