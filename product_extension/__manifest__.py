# -*- coding: utf-8 -*-
{
    "name": "Product Extension",
    'sequence': 4,
    "version": "18.0.1.0.0",
    "summary": "Adds code field to products and categories",
    "description": """
        This module extends product functionality with:
        - Code field for product templates
        - Code field for product categories
        - Code fields displayed on the same line as name fields
    """,
    "author": "Asmaa Hassaan",
    "depends": ["product", "stock", "sale_management"],
    "data": [
        "security/ir.model.access.csv",
        "data/product_reference_sequences.xml",
        "views/product_template_views.xml",
        "views/product_category_views.xml",
        "views/product_attribute_views.xml",
    ],
    "license": "LGPL-3",
    'installable': True,
    'auto_install': False,
    'application': True,
}

