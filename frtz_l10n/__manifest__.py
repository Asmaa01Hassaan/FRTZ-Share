# -*- coding: utf-8 -*-
{
    "name": "FRTZ Latin Digits for Arabic",
    "version": "18.0.1.0.0",
    "summary": "Use Western digits (0-9) when the UI language is Arabic",
    "category": "Hidden",
    "depends": ["web"],
    "assets": {
        "web.assets_backend": [
            "frtz_l10n/static/src/js/localization_patch.js",
        ],
    },
    "post_load": "post_load",
    "license": "LGPL-3",
    "installable": True,
    "auto_install": False,
}
