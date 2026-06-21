import json
import re


def migrate(cr, version):
  """Clean legacy Odoo 17 account.move form views before module data is loaded."""
  cr.execute(
    """
    SELECT id, arch_db
    FROM ir_ui_view
    WHERE model = 'account.move'
      AND (
        arch_db::text LIKE '%expected_currency_rate%'
        OR arch_db::text LIKE '%refresh_invoice_currency_rate%'
      )
    """
  )
  button_pattern = re.compile(
    r'<button[^>]*name="refresh_invoice_currency_rate"[^>]*/>\s*',
    re.MULTILINE,
  )
  for view_id, arch_db in cr.fetchall():
    if isinstance(arch_db, str):
      arch_db = json.loads(arch_db)
    new_arch_db = {}
    changed = False
    for lang, arch in arch_db.items():
      new_arch = arch.replace('expected_currency_rate', 'invoice_currency_rate')
      new_arch = button_pattern.sub('', new_arch)
      new_arch_db[lang] = new_arch
      changed = changed or new_arch != arch
    if changed:
      cr.execute(
        "UPDATE ir_ui_view SET arch_db = %s::jsonb, write_date = NOW() AT TIME ZONE 'UTC' WHERE id = %s",
        (json.dumps(new_arch_db), view_id),
      )
