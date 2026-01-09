# -*- coding: utf-8 -*-
{
    "name": "Product Extension",
    "version": "18.0.1.0.0",
    "summary": "Adds code field to products and categories",
    "description": """
        This module extends product functionality with:
        - Code field for product templates
        - Code field for product categories
        - Code fields displayed on the same line as name fields
    """,
    "author": "Your Company",
    "depends": ["product", "stock", "sale"],
    "data": [
        "security/ir.model.access.csv",
        "views/product_template_views.xml",
        "views/product_category_views.xml",
    ],
    "license": "LGPL-3",
    "application": False,
    "installable": True,
    "auto_install": False,
}

