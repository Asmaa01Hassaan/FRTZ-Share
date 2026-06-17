# -*- coding: utf-8 -*-

_ARABIC_INDIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_LATIN_DIGITS = "0123456789"
_DIGIT_TRANSLATION = str.maketrans(_ARABIC_INDIC_DIGITS, _LATIN_DIGITS)


def _to_latin_digits(value):
    if not value:
        return value
    return value.translate(_DIGIT_TRANSLATION)


def post_load():
    """Force Western digits in backend date/number formatting for Arabic locales."""
    import odoo.tools.misc as misc

    if getattr(misc, "_frtz_l10n_patched", False):
        return

    original_format_date = misc.format_date
    original_format_datetime = misc.format_datetime

    def format_date(env, value, lang_code=None, date_format=False):
        return _to_latin_digits(
            original_format_date(env, value, lang_code=lang_code, date_format=date_format)
        )

    def format_datetime(env, value, tz=False, dt_format="medium", lang_code=None):
        return _to_latin_digits(
            original_format_datetime(
                env, value, tz=tz, dt_format=dt_format, lang_code=lang_code
            )
        )

    misc.format_date = format_date
    misc.format_datetime = format_datetime
    misc._frtz_l10n_patched = True
