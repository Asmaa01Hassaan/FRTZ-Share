from odoo import models


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    def get_view_info(self):
        """Skip enterprise-only view types when their modules are unavailable."""
        view_info = self._get_view_info()
        return {
            view_type: {
                'display_name': display_name,
                'icon': view_info[view_type]['icon'],
                'multi_record': view_info[view_type].get('multi_record', True),
            }
            for view_type, display_name in self.fields_get(['type'], ['selection'])['type']['selection']
            if view_type != 'qweb' and view_type in view_info
        }
