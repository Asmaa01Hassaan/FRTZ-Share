# Product Extension Module

## Overview

This module extends product templates and product categories with a `code` field, similar to the customer code functionality in `frtz_customer` module.

## Features

### 1. Code Field
- Adds `code` field to `product.template`
- Adds `code` field to `product.category`
- Code appears on the same line as the name field in form views

### 2. Display Name
- Computes `display_name` as `"[CODE] [NAME]"` format
- Example: "PROD001 Laptop Computer"
- Used throughout Odoo (dropdowns, lists, search results)

### 3. Enhanced Search
- Search by product/category name
- Search by product/category code
- Both searches work simultaneously

### 4. Smart Display
- Products appear as "CODE NAME" in all views
- Categories appear as "CODE NAME" in all views
- Consistent formatting across the system

## How It Works

### Product Template

**Model:** `product.template`
- Field: `code` (Char)
- Field: `display_name` (Char, computed, stored)
- Method: `_compute_display_name()` - Combines code + name
- Method: `name_get()` - Returns formatted display name
- Method: `name_search()` - Searches by code or name

**View:** 
- Code field appears next to name in form header
- Uses flexbox layout for alignment

### Product Category

**Model:** `product.category`
- Field: `code` (Char)
- Field: `display_name` (Char, computed, stored)
- Method: `_compute_display_name()` - Combines code + name
- Method: `name_get()` - Returns formatted display name
- Method: `name_search()` - Searches by code or name

**View:**
- Code field appears next to name in form header

## Usage Examples

### Creating a Product
1. Go to Products > Create
2. Enter name: "Laptop Computer"
3. Enter code: "PROD001"
4. Both appear on same line: `[Laptop Computer] [PROD001]`
5. Display name becomes: "PROD001 Laptop Computer"

### Searching Products
- Type "PROD001" → Finds product
- Type "Laptop" → Finds product
- Both searches work because of `name_search` override

### Display
- In dropdowns: Shows "PROD001 Laptop Computer"
- In lists: Shows "PROD001 Laptop Computer"
- In forms: Shows name and code on same line

### Creating a Category
1. Go to Products > Configuration > Categories > Create
2. Enter name: "Electronics"
3. Enter code: "CAT001"
4. Both appear on same line: `[Electronics] [CAT001]`
5. Display name becomes: "CAT001 Electronics"

## Technical Details

### Display Name Computation
```python
@api.depends('name', 'code')
def _compute_display_name(self):
    for record in self:
        name = record.name or ''
        if record.code:
            name = f"{record.code} {name}"
        record.display_name = name
```

### Name Search Enhancement
```python
@api.model
def name_search(self, name='', args=None, operator='ilike', limit=100):
    if name:
        domain = ['|', ('name', operator, name), ('code', operator, name)]
    records = self.search(domain + args, limit=limit)
    return records.name_get()
```

## Benefits

✅ **Consistent with Customer Module** - Same pattern as frtz_customer  
✅ **Better Organization** - Code helps identify products/categories quickly  
✅ **Enhanced Search** - Find by code or name  
✅ **Professional Display** - "CODE NAME" format everywhere  
✅ **Visual Clarity** - Code and name on same line in forms  

