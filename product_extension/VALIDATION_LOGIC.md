# Validation Logic Documentation

## Current Validation Logic Flow

### 1. **Category Configuration** (`product.category`)

The category defines the validation rules:

```python
reference_type = fields.Selection([
    ('manual', 'Manual'),        # No validation, user enters freely
    ('validation', 'Validation'), # Validate user input
    ('automatic', 'Automatic'),   # System generates reference (NOT IMPLEMENTED)
], default='manual')
```

**When `reference_type == 'validation'`, additional fields are used:**

- `validation_mode`: 'length' or 'type'
- `reference_length`: Required length (for length mode)
- `reference_char_type`: 'number' or 'mix' (for type mode)

---

### 2. **Validation Process** (`_check_internal_reference_new`)

The validation runs when:
- `internal_reference_new` field changes
- `categ_id` (category) changes

**Flow Diagram:**

```
Product Created/Updated
    ↓
Has category? ──NO──→ Skip validation (allow any value)
    ↓ YES
reference_type == 'manual'? ──YES──→ Skip validation (allow any value)
    ↓ NO
reference_type == 'validation'? ──NO──→ Skip validation
    ↓ YES
    ├─ validation_mode == 'length'?
    │   ├─ reference_length set?
    │   │   ├─ YES → Check: len(ref) > reference_length? → ERROR
    │   │   └─ NO → Skip (no validation)
    │   └─ validation_mode == 'type'?
    │       ├─ reference_char_type == 'number'?
    │       │   └─ ref.isdigit()? → NO → ERROR
    │       └─ reference_char_type == 'mix'?
    │           └─ No validation (PASS - BUG!)
```

---

### 3. **Current Issues in Validation**

#### Issue 1: Length Validation is Wrong
```python
if len(ref) > cat.reference_length:  # ❌ WRONG
    raise ValidationError("must be exactly...")
```

**Problem:** Checks if length is GREATER than required, but error says "exactly"
- If length is LESS than required → No error (should error!)
- If length is EQUAL → No error (correct)
- If length is GREATER → Error (correct)

**Should be:**
```python
if len(ref) != cat.reference_length:  # ✅ CORRECT
    raise ValidationError("must be exactly...")
```

#### Issue 2: Empty Reference Not Validated
```python
ref = product.internal_reference_new or ''
if len(ref) > cat.reference_length:  # Empty string length is 0
```

**Problem:** Empty references pass validation when they shouldn't (if required)

#### Issue 3: 'mix' Validation Does Nothing
```python
if cat.reference_char_type == 'mix':
    pass  # ❌ No validation!
```

**Problem:** 'mix' mode doesn't validate anything

#### Issue 4: 'automatic' Mode Not Implemented
- Category can be set to 'automatic'
- But no code generates the reference automatically

---

## Recommendations for Automatic Reference Generation

### Option 1: **Sequence-Based (Recommended)**

Use Odoo's `ir.sequence` to generate unique references automatically.

**Advantages:**
- ✅ Standard Odoo pattern
- ✅ Guaranteed uniqueness
- ✅ Configurable format (prefix, padding, etc.)
- ✅ Per-category sequences possible

**Implementation:**

1. **Add sequence field to category:**
```python
# In product_category.py
reference_sequence_id = fields.Many2one(
    'ir.sequence',
    string="Reference Sequence",
    help="Sequence to use for automatic reference generation"
)
```

2. **Create sequence data file:**
```xml
<!-- data/product_reference_sequences.xml -->
<odoo>
    <data noupdate="1">
        <!-- Default sequence for products -->
        <record id="seq_product_reference_default" model="ir.sequence">
            <field name="name">Product Internal Reference</field>
            <field name="code">product.internal.reference</field>
            <field name="prefix">PRD</field>
            <field name="padding">6</field>
            <field name="number_next">1</field>
        </record>
    </data>
</odoo>
```

3. **Auto-generate on create:**
```python
# In product_template.py
@api.model
def create(self, vals):
    # Generate reference if category is set to automatic
    if not vals.get('internal_reference_new'):
        categ_id = vals.get('categ_id')
        if categ_id:
            category = self.env['product.category'].browse(categ_id)
            if category.reference_type == 'automatic':
                sequence = category.reference_sequence_id or \
                    self.env.ref('product_extension.seq_product_reference_default')
                if sequence:
                    vals['internal_reference_new'] = sequence.next_by_id()
    return super().create(vals)
```

4. **Make field readonly when automatic:**
```xml
<!-- In product_template_views.xml -->
<field name="internal_reference_new" 
       readonly="categ_id.reference_type == 'automatic'"/>
```

---

### Option 2: **Pattern-Based Generation**

Generate references based on category code + pattern.

**Example:**
- Category code: "ELEC"
- Pattern: "{CATEGORY_CODE}-{SEQUENCE}"
- Result: "ELEC-000001", "ELEC-000002", etc.

**Implementation:**
```python
@api.model
def create(self, vals):
    if not vals.get('internal_reference_new'):
        categ_id = vals.get('categ_id')
        if categ_id:
            category = self.env['product.category'].browse(categ_id)
            if category.reference_type == 'automatic':
                # Get category code or use default
                prefix = category.code or 'PRD'
                
                # Find last reference with this prefix
                last_ref = self.search([
                    ('internal_reference_new', '=like', f'{prefix}-%')
                ], order='internal_reference_new desc', limit=1)
                
                # Extract number and increment
                if last_ref and last_ref.internal_reference_new:
                    try:
                        last_num = int(last_ref.internal_reference_new.split('-')[-1])
                        next_num = last_num + 1
                    except:
                        next_num = 1
                else:
                    next_num = 1
                
                # Format with padding
                padding = category.reference_length or 6
                vals['internal_reference_new'] = f"{prefix}-{next_num:0{padding}d}"
    
    return super().create(vals)
```

---

### Option 3: **Smart Generation with Validation Rules**

Combine automatic generation with category validation rules.

**Example:**
- Category: Electronics, length=8, type=number
- Generated: "00000001", "00000002", etc.

**Implementation:**
```python
def _generate_automatic_reference(self, category):
    """Generate reference based on category validation rules"""
    # Get sequence number
    sequence = category.reference_sequence_id or \
        self.env.ref('product_extension.seq_product_reference_default')
    base_ref = sequence.next_by_id() or "1"
    
    # Apply validation rules if set
    if category.validation_mode == 'length':
        length = category.reference_length or 6
        # Pad or truncate to required length
        if category.reference_char_type == 'number':
            # Ensure numeric
            base_ref = base_ref.lstrip('0') or '0'
            base_ref = base_ref.zfill(length)
        else:
            # Mixed: use prefix + padded number
            prefix = (category.code or 'PRD')[:max(0, length - len(base_ref))]
            base_ref = (prefix + base_ref).ljust(length, '0')[:length]
    
    return base_ref
```

---

## Recommended Implementation Plan

### Phase 1: Fix Current Validation Issues
1. ✅ Fix length validation (use `!=` instead of `>`)
2. ✅ Add empty reference check
3. ✅ Add 'mix' validation (if needed) or remove it
4. ✅ Add required field validation

### Phase 2: Implement Automatic Generation
1. ✅ Add `reference_sequence_id` to category
2. ✅ Create default sequence
3. ✅ Implement `create()` method to auto-generate
4. ✅ Make field readonly when automatic
5. ✅ Add UI to configure sequence per category

### Phase 3: Enhanced Features (Optional)
1. ⭐ Per-category sequences
2. ⭐ Pattern-based generation
3. ⭐ Reference regeneration option
4. ⭐ Bulk reference generation for existing products

---

## Example: Complete Fixed Validation

```python
@api.constrains('internal_reference_new', 'categ_id')
def _check_internal_reference_new(self):
    for product in self:
        cat = product.categ_id
        ref = product.internal_reference_new or ''

        # Skip if no category or manual mode
        if not cat or cat.reference_type == 'manual':
            continue
        
        # Skip validation if automatic (system generates)
        if cat.reference_type == 'automatic':
            continue
        
        # Validation mode: check rules
        if cat.reference_type == 'validation':
            # Check if reference is required (when validation is enabled)
            if not ref:
                raise ValidationError(
                    "Internal Reference is required for category '%s'." % cat.name
                )
            
            # Length validation
            if cat.validation_mode == 'length':
                if not cat.reference_length:
                    continue  # No length set, skip
                if len(ref) != cat.reference_length:  # ✅ FIXED: use != instead of >
                    raise ValidationError(
                        f"Internal Reference must be exactly "
                        f"{cat.reference_length} characters. "
                        f"Current length: {len(ref)}"
                    )
            
            # Type validation
            if cat.validation_mode == 'type':
                if cat.reference_char_type == 'number':
                    if not ref.isdigit():
                        raise ValidationError(
                            "Internal Reference must contain numbers only."
                        )
                elif cat.reference_char_type == 'mix':
                    # Validate mix: must contain at least one letter and one number
                    if not (any(c.isalpha() for c in ref) and 
                            any(c.isdigit() for c in ref)):
                        raise ValidationError(
                            "Internal Reference must contain both letters and numbers."
                        )
```

---

## Summary

**Current State:**
- ✅ Manual mode works (no validation)
- ⚠️ Validation mode partially works (has bugs)
- ❌ Automatic mode not implemented

**Recommended Next Steps:**
1. Fix validation bugs first
2. Implement sequence-based automatic generation
3. Add per-category sequence configuration
4. Test thoroughly with different scenarios

