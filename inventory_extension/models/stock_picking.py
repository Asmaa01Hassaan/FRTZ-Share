# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    operation_type_code = fields.Char(
        string="Operation Type Code",
        compute="_compute_operation_type_code",
        store=False,
        help="Used to filter operation types"
    )

    entry_type = fields.Selection(
        [('consignment', 'Consignment')],
        string="Entry Type",
        help="Type of entry for receiving goods"
    )
    
    @api.onchange('picking_type_id')
    def _onchange_picking_type_id_entry_type(self):
        """Clear entry_type when picking_type_id changes to non-incoming"""
        if self.picking_type_id and self.picking_type_id.code != 'incoming':
            self.entry_type = False

    @api.depends('picking_type_id.code')
    def _compute_operation_type_code(self):
        """Compute the operation type code for domain filtering"""
        for record in self:
            if record.picking_type_id:
                record.operation_type_code = record.picking_type_id.code
            else:
                # Try to get from context (set by menu action)
                default_picking_type_id = self.env.context.get('default_picking_type_id')
                if default_picking_type_id:
                    picking_type = self.env['stock.picking.type'].browse(default_picking_type_id)
                    if picking_type.exists():
                        record.operation_type_code = picking_type.code
                    else:
                        record.operation_type_code = False
                else:
                    record.operation_type_code = False

    @api.onchange('picking_type_id')
    def _onchange_picking_type_id(self):
        """Update operation_type_code when picking_type_id changes"""
        if self.picking_type_id:
            self.operation_type_code = self.picking_type_id.code

