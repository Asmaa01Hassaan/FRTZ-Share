# -*- coding: utf-8 -*-

def post_init_hook(env):
    """Backfill installment payment status for invoices already marked as paid."""
    moves = env['account.move'].search([
        ('move_type', 'in', ('out_invoice', 'out_refund', 'out_receipt', 'in_invoice', 'in_refund', 'in_receipt')),
        ('state', '=', 'posted'),
        ('payment_state', '=', 'paid'),
    ])
    moves = moves.filtered(
        lambda move: move.installment_ids.filtered(lambda inst: inst.amount_residual > 0)
    )
    if moves:
        moves._sync_installments_on_invoice_paid()
