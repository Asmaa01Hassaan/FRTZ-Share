# -*- coding: utf-8 -*-
{
    "name": "Inventory Extension",
    "version": "18.0.1.0.0",
    "summary": "Filter Operation Type based on document type",
    "description": """
        This module filters the Operation Type dropdown in stock pickings
        to show only relevant operation types based on the document type:
        - Receipts: Only show incoming operation types
        - Deliveries: Only show outgoing operation types
        - Internal Transfers: Only show internal operation types
    """,
    "author": "Omar Radwan",
    "depends": ["stock"],
    "data": [
        "views/stock_picking_views.xml",
    ],
    "license": "LGPL-3",
    "application": False,
    "installable": True,
}

