# models/sale_order.py
from odoo import Command, models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.models import NewId
from odoo.tools import float_compare


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    _PAYMENT_PLAN_TO_PAY_TYPE = {
        'immediate': 'spot',
        'regular': 'fixed',
        'irregular': 'custom',
    }

    vendor_name_id = fields.Many2one('res.partner', string='Vendor Name')
    payment_type = fields.Selection(
        [
            ('immediate', 'Spot(Full)'),
            ('regular', 'Fixed(Auto)'),
            ('irregular', 'Custom(Manual)'),
        ],
        string="Payment plan",
        default="regular",
        tracking=True,
        copy=False,
        help="Select the payment plan for this order"
    )
    pay_type = fields.Selection(
        [
            ('spot', 'Spot(Full)'),
            ('fixed', 'Fixed(Auto)'),
            ('custom', 'Custom(Manual)'),
        ],
        string="Payment Plan",
        default='fixed',
        copy=False,
        help="Type of payment plan",
    )
    installment_count = fields.Integer(
        string="Installments Num.",
        default=0,
        copy=False,
        help="Number of installments for this payment term",
    )
    first_payment_type = fields.Selection(
        [
            ('percent', 'Percent'),
            ('fixed', 'Fixed'),
        ],
        string="First Payment Type",
        default='fixed',
        copy=False,
        help="Type of first payment: percent or fixed amount",
    )
    first_payment_percentage = fields.Float(
        string="First Payment",
        default=0.0,
        digits=(16, 2),
        copy=False,
        help="First payment value",
    )
    show_installment_scope = fields.Boolean(compute='_compute_installment_config_visibility')
    readonly_installment_scope = fields.Boolean(compute='_compute_installment_config_visibility')
    show_installment_baseline_date = fields.Boolean(compute='_compute_installment_config_visibility')
    readonly_installment_baseline_date = fields.Boolean(compute='_compute_installment_config_visibility')

    scope = fields.Selection([
        ('per_invoice', 'Per Invoice'),
        ('per_lines', 'Per Lines'),
    ], string="Scope",
        default=lambda self: self.env['installment.config.mixin']._get_installment_default_scope(),
        help="Scope of payment term application")
    apply_payment_term_per_line = fields.Boolean(
        string='Apply Payment Term Per Line',
        compute='_compute_apply_payment_term_per_line',
        store=True,
    )
    baseline_date = fields.Selection(
        [
            ('invoice_date', 'Invoice Date'),
            ('posting_date', 'Posting Date'),
            ('receipt_date', 'Receipt Date'),
        ],
        string="Baseline Date",
        default=lambda self: self.env['installment.config.mixin']._get_installment_default_baseline_date(),
        copy=False,
        help="Baseline date for payment term calculation",
    )
    settlement_trigger = fields.Selection(
        [
            ('cia', 'CIA-Cash in Advance'),
            ('cod', 'Cash on Delivery'),
            ('cbd', 'Cash Before Delivery'),
        ],
        string="Payment Timing",
        default='cia',
        copy=False,
        help="Settlement trigger type for spot payment plans",
    )
    installment_frequency = fields.Selection(
        [
            ('monthly', 'Monthly'),
            ('weekly', 'Weekly'),
            ('daily', 'Daily'),
        ],
        string="Installment Frequency",
        default='monthly',
        copy=False,
        help="Frequency of installments for fixed payment plans",
    )
    installment_preview_ids = fields.One2many(
        'sale.order.installment',
        'sale_order_id',
        string='Installment Preview',
        copy=False,
    )
    has_installments = fields.Boolean(
        string='Has Installments',
        compute='_compute_installment_preview_totals',
    )
    total_installment_count = fields.Integer(
        string='Total Installment Count',
        compute='_compute_installment_preview_totals',
    )
    installment_preview_count = fields.Integer(
        string='Installment Preview Count',
        compute='_compute_installment_preview_totals',
    )
    total_installment_amount = fields.Monetary(
        string='Total Installment Amount',
        currency_field='currency_id',
        compute='_compute_installment_preview_totals',
    )
    nearest_due_installment_amount = fields.Monetary(
        string='Nearest Due Installment Amount',
        currency_field='currency_id',
        compute='_compute_installment_preview_totals',
    )
    nearest_due_installment_date = fields.Date(
        string='Nearest Due Installment Date',
        compute='_compute_installment_preview_totals',
    )
    name = fields.Char('Plan Name', required=True, translate=True)

    # Order Type Classification (legacy installment order typing).
    # Renamed from `order_type` to `installment_order_type` to avoid a hard field
    # collision with sales_order_extension's `order_type` Char (which mirrors
    # sale.order.type). Behaviour is unchanged: same values, same sequence map.
    installment_order_type = fields.Selection([
        ('standard', 'Standard Sale Order'),
        ('custom', 'Warehouse Sale Order'),
        ('wholesale', 'External Sales Order'),
        ('subscription', 'Service Sales Order'),
    ], string='Order Type', default='standard', required=True, tracking=True,
       help="Select the type of sale order")

    def _compute_installment_config_visibility(self):
        states = self.env['installment.config.mixin']._get_installment_field_ui_states()
        for order in self:
            order.show_installment_scope = states['show_installment_scope']
            order.readonly_installment_scope = states['readonly_installment_scope']
            order.show_installment_baseline_date = states['show_installment_baseline_date']
            order.readonly_installment_baseline_date = states['readonly_installment_baseline_date']

    @api.model
    def default_get(self, fields_list):
        return self.env['installment.config.mixin']._apply_installment_config_defaults(
            fields_list,
            super().default_get(fields_list),
        )

    @api.depends('scope')
    def _compute_apply_payment_term_per_line(self):
        for order in self:
            order.apply_payment_term_per_line = order.scope == 'per_lines'

    def _get_total_line_first_payment_amount(self):
        """Sum of down payments configured on order lines (per-lines scope)."""
        self.ensure_one()
        if not self.apply_payment_term_per_line:
            return 0.0
        total = sum(
            line._get_line_first_payment_amount(line.price_total or 0.0)
            for line in self.order_line.filtered(lambda item: not item.display_type)
        )
        return self.currency_id.round(total) if self.currency_id else total

    def _update_order_line_payment_terms_from_values(self, line_ids=None):
        for order in self.filtered(lambda item: item.apply_payment_term_per_line):
            lines = order.order_line.filtered(lambda line: not line.display_type)
            if line_ids is not None:
                lines = lines.filtered(lambda line: line.id in line_ids)
            lines._generate_line_payment_terms_from_values()

    def _sync_payment_plan_values(self, vals, use_defaults=False):
        vals = dict(vals)
        if use_defaults:
            vals.setdefault('scope', self.env['installment.config.mixin']._get_installment_default_scope())
        payment_type = vals.get('payment_type')
        if use_defaults and not payment_type and 'pay_type' not in vals:
            payment_type = 'regular'
        if payment_type in self._PAYMENT_PLAN_TO_PAY_TYPE and 'pay_type' not in vals:
            vals['pay_type'] = self._PAYMENT_PLAN_TO_PAY_TYPE[payment_type]
        if vals.get('pay_type') == 'spot':
            vals['first_payment_type'] = 'percent'
            vals['first_payment_percentage'] = 100.0
        elif vals.get('pay_type') in ('fixed', 'custom') and 'first_payment_percentage' not in vals:
            vals['first_payment_percentage'] = 0.0
        return vals

    @api.depends('installment_preview_ids.amount_total', 'installment_preview_ids.date_due')
    def _compute_installment_preview_totals(self):
        for order in self:
            installments = order.installment_preview_ids
            order.has_installments = bool(installments)
            order.total_installment_count = len(installments)
            order.installment_preview_count = order.total_installment_count
            order.total_installment_amount = sum(installments.mapped('amount_total'))
            upcoming = installments.filtered(lambda installment: installment.amount_residual > 0).sorted('date_due')
            nearest = upcoming[:1]
            order.nearest_due_installment_amount = nearest.amount_residual if nearest else 0.0
            order.nearest_due_installment_date = nearest.date_due if nearest else False

    @api.model
    def _uses_sale_order_type_sequence(self, vals):
        if "sale.order.type" not in self.env:
            return False
        return bool(
            vals.get("sale_order_type_id")
            or self.env.context.get("default_sale_order_type_id")
        )

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate sequence based on order type"""
        vals_list = [self._sync_payment_plan_values(vals, use_defaults=True) for vals in vals_list]
        for vals in vals_list:
            if vals.get('name', 'New') != _('New'):
                continue
            if self._uses_sale_order_type_sequence(vals):
                continue
            # Legacy installment_order_type sequences (when sale.order.type is not used).
            installment_order_type = vals.get('installment_order_type', 'standard')
            sequence_map = {
                'standard': 'sale.order',
                'custom': 'custom.sale.order',
                'wholesale': 'wholesale.sale.order',
                'subscription': 'subscription.sale.order',
            }
            seq_code = sequence_map.get(installment_order_type, 'sale.order')

            try:
                seq_date = fields.Datetime.context_timestamp(
                    self, fields.Datetime.to_datetime(vals.get('date_order'))
                ) if vals.get('date_order') else None
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    seq_code, sequence_date=seq_date
                ) or _('New')
            except Exception:
                vals['name'] = self.env['ir.sequence'].next_by_code('sale.order') or _('New')
        orders = super().create(vals_list)
        for order in orders:
            if order.apply_payment_term_per_line:
                order._update_order_line_payment_terms_from_values()
            order.with_context(skip_auto_generate_sale_payment_term=True).generate_order_payment_term()
        return orders

    def write(self, vals):
        payment_plan_fields = {
            'payment_type',
            'pay_type',
            'installment_count',
            'installment_frequency',
            'first_payment_type',
            'first_payment_percentage',
            'baseline_date',
            'settlement_trigger',
            'scope',
            'payment_term_id',
            'order_line',
            'date_order',
        }
        if vals.get('scope') == 'per_invoice':
            vals['apply_payment_term_per_line'] = False
        elif vals.get('scope') == 'per_lines':
            vals['apply_payment_term_per_line'] = True
        vals = self._sync_payment_plan_values(vals) if {'payment_type', 'pay_type'} & vals.keys() else vals
        result = super().write(vals)
        if not self.env.context.get('skip_auto_generate_sale_payment_term') and payment_plan_fields & vals.keys():
            for order in self:
                if order.apply_payment_term_per_line and 'order_line' not in vals:
                    order._update_order_line_payment_terms_from_values()
                order.with_context(skip_auto_generate_sale_payment_term=True).generate_order_payment_term()
        return result

    @api.onchange('payment_term_id')
    def _onchange_payment_term_id_scope(self):
        if self.payment_term_id and hasattr(self.payment_term_id, 'scope'):
            self.scope = self.payment_term_id.scope
            if self.scope == 'per_lines':
                for line in self.order_line.filtered(lambda item: not item.display_type):
                    if not line.payment_term_id:
                        line.payment_term_id = self.payment_term_id

    @api.onchange('scope')
    def _onchange_scope_payment_terms(self):
        if self.scope == 'per_lines' and self.payment_term_id:
            for line in self.order_line.filtered(lambda item: not item.display_type):
                if not line.payment_term_id:
                    line.payment_term_id = self.payment_term_id

    @api.onchange('payment_type')
    def _onchange_payment_type_pay_type(self):
        for order in self:
            order.pay_type = self._PAYMENT_PLAN_TO_PAY_TYPE.get(order.payment_type, order.pay_type)
            if order.pay_type == 'spot':
                order.first_payment_type = 'percent'
                order.first_payment_percentage = 100.0
            elif order.pay_type in ('fixed', 'custom'):
                order.first_payment_percentage = 0.0

    @api.onchange('pay_type')
    def _onchange_pay_type_first_payment(self):
        for order in self:
            if order.pay_type == 'spot':
                order.first_payment_type = 'percent'
                order.first_payment_percentage = 100.0
            elif order.pay_type in ('fixed', 'custom'):
                order.first_payment_percentage = 0.0

    def _create_account_invoices(self, invoice_vals_list, final):
        """Preserve SO payment terms on invoice create (skip auto-regeneration)."""
        return super(
            SaleOrder,
            self.with_context(
                skip_auto_generate_payment_term=True,
                skip_line_payment_term_generation=True,
            ),
        )._create_account_invoices(invoice_vals_list, final)

    def _prepare_invoice(self):
        self.ensure_one()
        invoice_vals = super()._prepare_invoice()
        invoice_vals.update({
            'payment_type': self.payment_type,
            'pay_type': self.pay_type,
            'installment_count': self.installment_count,
            'first_payment_type': self.first_payment_type,
            'first_payment_percentage': self.first_payment_percentage,
            'scope': self.scope,
            'apply_payment_term_per_line': self.apply_payment_term_per_line,
            'baseline_date': self.baseline_date,
            'settlement_trigger': self.settlement_trigger,
            'installment_frequency': self.installment_frequency,
            'invoice_payment_term_id': self.payment_term_id.id,
        })
        return invoice_vals

    def _build_payment_term_vals(self):
        self.ensure_one()
        pay_type = self.pay_type or self._PAYMENT_PLAN_TO_PAY_TYPE.get(self.payment_type) or 'spot'
        vals = {
            'company_id': self.company_id.id,
            'is_installment_term': True,
            'pay_type': pay_type,
            'installment_count': self.installment_count,
            'first_payment_type': self.first_payment_type,
            'first_payment_percentage': self.first_payment_percentage,
            'baseline_date': self.baseline_date,
            'settlement_trigger': self.settlement_trigger,
            'scope': self.scope,
        }
        if pay_type == 'fixed':
            vals['installment_frequency'] = self.installment_frequency or 'monthly'
        vals['line_ids'] = self._build_payment_term_line_commands(pay_type)
        return vals

    def _build_payment_term_line_commands(self, pay_type):
        self.ensure_one()
        first_payment = self.first_payment_percentage or 0.0
        if self.first_payment_type == 'percent' and not (0 <= first_payment <= 100):
            raise ValidationError(_("First Payment (%) must be between 0 and 100."))

        if pay_type == 'spot':
            if self.first_payment_type == 'fixed' and first_payment > 0:
                return [
                    (0, 0, {
                        'value': 'fixed',
                        'value_amount': first_payment,
                        'nb_days': 0,
                        'delay_type': 'days_after',
                    }),
                    (0, 0, {
                        'value': 'percent',
                        'value_amount': 100.0,
                        'nb_days': 0,
                        'delay_type': 'days_after',
                    }),
                ]
            return [(0, 0, {
                'value': 'percent',
                'value_amount': 100.0,
                'nb_days': 0,
                'delay_type': 'days_after',
            })]

        if pay_type != 'fixed' or self.installment_count < 1:
            return [(0, 0, {
                'value': 'percent',
                'value_amount': 100.0,
                'nb_days': 0,
                'delay_type': 'days_after',
            })]

        lines = []
        if first_payment > 0:
            lines.append((0, 0, {
                'value': self.first_payment_type,
                'value_amount': first_payment,
                'nb_days': 0,
                'delay_type': 'days_after',
            }))

        days_map = {
            'monthly': 30,
            'weekly': 7,
            'daily': 1,
        }
        days_interval = days_map.get(self.installment_frequency or 'monthly', 30)
        percent_to_split = 100.0
        if self.first_payment_type == 'percent':
            percent_to_split -= first_payment

        installment_count = int(self.installment_count)
        base_percentage = percent_to_split / installment_count
        percent_so_far = 100.0 - percent_to_split

        for index in range(installment_count):
            if index == installment_count - 1:
                value_amount = 100.0 - percent_so_far
            else:
                value_amount = base_percentage
                percent_so_far += value_amount
            lines.append((0, 0, {
                'value': 'percent',
                'value_amount': value_amount,
                'nb_days': (index + 1) * days_interval,
                'delay_type': 'days_after',
            }))

        return lines

    def _create_payment_term_from_plan(self):
        self.ensure_one()
        if self.pay_type == 'fixed' and self.installment_count < 1:
            return False

        PaymentTerm = self.env['account.payment.term']
        term_vals = self._build_payment_term_vals()
        term_preview = PaymentTerm.new(term_vals)
        term_vals['name'] = term_preview._generate_auto_name() or _("Installments - %s") % self.name
        return PaymentTerm.create(term_vals)

    def action_open_order_payment_term(self):
        """Create/open the manual payment term used by irregular sale orders."""
        self.ensure_one()
        if self.payment_type != 'irregular' and self.pay_type != 'custom':
            return False

        if not self.payment_term_id:
            term_vals = self._build_payment_term_vals()
            term_vals.update({
                'pay_type': 'custom',
                'name': _("Manual Installments - %s") % (self.name or _("Sale Order")),
            })
            term = self.env['account.payment.term'].create(term_vals)
            self.with_context(skip_auto_generate_sale_payment_term=True).write({
                'payment_term_id': term.id,
            })
        action = self.payment_term_id.get_formview_action()
        action['target'] = 'new'
        action['context'] = {
            'default_company_id': self.company_id.id,
            'default_is_installment_term': True,
            'default_pay_type': 'custom',
            'default_scope': self.scope,
            'default_baseline_date': self.baseline_date,
            'default_first_payment_type': self.first_payment_type,
            'default_first_payment_percentage': self.first_payment_percentage,
        }
        return action

    def generate_order_payment_term(self):
        for order in self:
            if not order.apply_payment_term_per_line:
                if order.payment_type in ('immediate', 'regular'):
                    term = order._create_payment_term_from_plan()
                    if term:
                        order.with_context(skip_auto_generate_sale_payment_term=True).write({
                            'payment_term_id': term.id,
                        })
                    elif order.payment_type == 'regular':
                        order.with_context(skip_auto_generate_sale_payment_term=True).write({
                            'payment_term_id': False,
                        })
            if order.apply_payment_term_per_line:
                order.order_line.filtered(lambda line: not line.display_type)._generate_line_payment_terms_from_values()
            order._regenerate_installment_preview()
        return True

    def _installment_preview_vals_for_memory(self, vals):
        """Strip parent/line ids that are not yet persisted (onchange/new form)."""
        cleaned = {}
        for key, value in vals.items():
            if key == 'sale_order_id':
                continue
            if key == 'sale_order_line_id' and (
                not value or isinstance(value, NewId)
            ):
                continue
            cleaned[key] = value
        return cleaned

    def _regenerate_installment_preview(self):
        if self.env.context.get('regenerating_installment_preview'):
            return
        Installment = self.env['sale.order.installment']
        orders = self.with_context(regenerating_installment_preview=True)
        for order in orders:
            date_ref = fields.Date.to_date(order.date_order) or fields.Date.today()
            if order.apply_payment_term_per_line:
                installments = order._calculate_installment_preview_per_line(date_ref)
            else:
                payment_term = order.payment_term_id
                if (
                    not payment_term
                    or not payment_term.is_installment_term
                    or not payment_term.line_ids
                ):
                    installments = []
                elif float_compare(order.amount_total, 0.0, precision_digits=2) == 0:
                    installments = []
                else:
                    installments = order._calculate_installment_preview_lines(
                        payment_term,
                        order.amount_total,
                        date_ref,
                        line_name=_('Order Total'),
                    )

            if isinstance(order.id, NewId):
                preview_commands = [Command.clear()]
                for vals in installments:
                    preview_commands.append(
                        Command.create(order._installment_preview_vals_for_memory(vals))
                    )
                order.installment_preview_ids = preview_commands
                continue

            order.installment_preview_ids.unlink()
            if installments:
                Installment.create(installments)

    def _sync_order_lines_from_payment_terms(self):
        """Fill line installment columns from each line's payment term (custom per-lines)."""
        if self.env.context.get('syncing_order_lines_from_payment_terms'):
            return
        for order in self.with_context(syncing_order_lines_from_payment_terms=True).filtered(
            lambda item: item.apply_payment_term_per_line and item.payment_type == 'irregular'
        ):
            for line in order.order_line.filtered(
                lambda item: not item.display_type and item.payment_term_id
            ):
                plan_values = line._get_plan_values_from_payment_term(line.payment_term_id)
                if not plan_values:
                    continue
                if isinstance(order.id, NewId):
                    line._apply_plan_values_from_payment_term(line.payment_term_id)
                    continue
                current = {
                    'line_installment_count': line.line_installment_count,
                    'line_first_payment_type': line.line_first_payment_type,
                    'line_first_payment_percentage': line.line_first_payment_percentage,
                }
                if all(current.get(key) == plan_values.get(key) for key in current):
                    continue
                line.with_context(
                    skip_sale_line_payment_term_generation=True,
                    skip_auto_generate_sale_payment_term=True,
                    skip_recompute_price_from_installments=True,
                ).write(plan_values)

    def _calculate_installment_preview_per_line(self, date_ref):
        self.ensure_one()
        installments = []
        for line in self.order_line.filtered(lambda sale_line: not sale_line.display_type):
            payment_term = line.payment_term_id
            if not payment_term or not payment_term.is_installment_term or not payment_term.line_ids:
                continue
            amount = line.price_total
            if float_compare(amount, 0.0, precision_digits=2) == 0:
                continue
            line_installments = self._calculate_installment_preview_lines(
                payment_term,
                amount,
                date_ref,
                line_name=line.name or line.product_id.display_name,
                sale_order_line=line,
            )
            installments.extend(line_installments)
        return installments

    def _calculate_installment_preview_lines(self, payment_term, amount, date_ref, line_name='', sale_order_line=False):
        self.ensure_one()
        installments = []
        sequence = 1
        for term_line in payment_term.line_ids:
            due_date = term_line._get_due_date(date_ref)
            if term_line.value == 'percent':
                installment_amount = amount * (term_line.value_amount / 100.0)
            elif term_line.value == 'fixed':
                installment_amount = self.company_id.currency_id._convert(
                    term_line.value_amount,
                    self.currency_id,
                    self.company_id,
                    date_ref,
                )
            else:
                continue

            installment_amount = self.currency_id.round(installment_amount)
            installments.append({
                'sale_order_id': self.id if isinstance(self.id, int) else False,
                'sale_order_line_id': (
                    sale_order_line.id
                    if sale_order_line and isinstance(sale_order_line.id, int)
                    else False
                ),
                'name': _('%s - Installment %s') % (line_name or _('Order Total'), sequence),
                'sequence': sequence,
                'amount_total': installment_amount,
                'date_due': due_date,
                'payment_term_line_id': term_line.id,
            })
            sequence += 1

        if installments:
            total_installments = sum(installment['amount_total'] for installment in installments)
            difference = amount - total_installments
            if float_compare(abs(difference), 0.01, precision_digits=2) > 0:
                installments[-1]['amount_total'] = self.currency_id.round(
                    installments[-1]['amount_total'] + difference
                )

        return installments

    def action_create_standard(self):
        """Create a new standard sale order"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('New Standard Sale Order'),
            'res_model': 'sale.order',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_order_type': 'standard'},
        }

    def action_create_custom(self):
        """Create a new custom sale order"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('New Custom Sale Order'),
            'res_model': 'sale.order',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_order_type': 'custom'},
        }

    def action_create_wholesale(self):
        """Create a new wholesale order"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('New Wholesale Order'),
            'res_model': 'sale.order',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_order_type': 'wholesale'},
        }

    def action_create_subscription(self):
        """Create a new subscription order"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('New Subscription Order'),
            'res_model': 'sale.order',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_order_type': 'subscription'},
        }


class SaleOrderInstallment(models.Model):
    _name = 'sale.order.installment'
    _description = 'Sale Order Installment Preview'
    _order = 'sequence, date_due'

    name = fields.Char(string='Installment Number', required=True, default='/')
    sequence = fields.Integer(string='Sequence', default=1, required=True)
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sale_order_line_id = fields.Many2one(
        'sale.order.line',
        string='Sale Order Line',
        ondelete='cascade',
    )
    partner_id = fields.Many2one('res.partner', string='Partner', related='sale_order_id.partner_id', store=True)
    company_id = fields.Many2one('res.company', string='Company', related='sale_order_id.company_id', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', related='sale_order_id.currency_id', store=True)
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        related='sale_order_line_id.product_id',
        store=True,
    )
    date_order = fields.Datetime(string='Order Date', related='sale_order_id.date_order', store=True)
    amount_total = fields.Monetary(
        string='Due Amount',
        currency_field='currency_id',
        required=True,
    )
    amount_paid = fields.Monetary(
        string='Amount Paid',
        currency_field='currency_id',
        default=0.0,
        readonly=True,
    )
    amount_residual = fields.Monetary(
        string='Remaining Amount',
        currency_field='currency_id',
        compute='_compute_amount_residual',
        store=True,
    )
    date_due = fields.Date(string='Due Date', required=True, index=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('due', 'Due'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('overdue', 'Overdue'),
    ], string='Status', default='draft', compute='_compute_state', store=True)
    payment_term_line_id = fields.Many2one(
        'account.payment.term.line',
        string='Payment Term Line',
    )
    notes = fields.Text(string='Notes')

    @api.depends('amount_total', 'amount_paid')
    def _compute_amount_residual(self):
        for installment in self:
            installment.amount_residual = installment.amount_total - (installment.amount_paid or 0.0)

    @api.depends('amount_residual', 'amount_paid', 'date_due')
    def _compute_state(self):
        today = fields.Date.today()
        for installment in self:
            if installment.amount_residual <= 0:
                installment.state = 'paid'
            elif installment.amount_paid > 0:
                installment.state = 'partial'
            elif installment.date_due and installment.date_due < today:
                installment.state = 'overdue'
            elif installment.date_due and installment.date_due >= today:
                installment.state = 'due'
            else:
                installment.state = 'draft'


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    payment_term_id = fields.Many2one(
        'account.payment.term',
        string='Payment Term',
        domain="[('is_installment_term', '=', True)]",
        help='Payment term for this sale order line. Used when the order scope is Per Lines.',
    )
    line_installment_count = fields.Integer(
        string='Installments Num.',
        default=0,
    )
    line_first_payment_type = fields.Selection(
        [
            ('percent', 'Percent'),
            ('fixed', 'Fixed'),
        ],
        string='First Payment Type',
        default='fixed',
    )
    line_first_payment_percentage = fields.Float(
        string='First Payment',
        default=0.0,
    )
    line_due_amount = fields.Monetary(
        string='Due Amt.',
        compute='_compute_line_payment_amounts',
        currency_field='currency_id',
        help='Total amount minus the first payment.',
    )
    line_installment_amount = fields.Monetary(
        string='Inst. Amt.',
        compute='_compute_line_payment_amounts',
        currency_field='currency_id',
        help='Amount of the first installment after the first payment.',
    )

    @api.depends(
        'price_total',
        'line_first_payment_type',
        'line_first_payment_percentage',
        'line_installment_count',
        'payment_term_id',
        'payment_term_id.line_ids',
        'currency_id',
        'order_id.date_order',
    )
    def _compute_line_payment_amounts(self):
        for line in self:
            total = line.price_total or 0.0
            if line.payment_term_id:
                date_ref = fields.Date.to_date(line.order_id.date_order) or fields.Date.today()
                breakdown = line.payment_term_id.get_line_payment_amount_breakdown(
                    total,
                    currency=line.currency_id,
                    company=line.company_id,
                    date_ref=date_ref,
                )
                line.line_due_amount = breakdown['due_amount']
                line.line_installment_amount = breakdown['first_installment_amount']
                continue
            first_pay = line._get_line_first_payment_amount(total)
            line.line_due_amount = total - first_pay
            line.line_installment_amount = line._get_line_first_installment_amount(total, first_pay)

    def _get_line_first_payment_amount(self, total):
        self.ensure_one()
        if not total:
            return 0.0
        if self.line_first_payment_type == 'fixed':
            return min(self.line_first_payment_percentage or 0.0, total)
        pct = self.line_first_payment_percentage or 0.0
        return total * (pct / 100.0)

    def _get_line_first_installment_amount(self, total, first_pay):
        self.ensure_one()
        count = self.line_installment_count or 0
        if not total or count < 1:
            return 0.0
        if self.line_first_payment_type == 'percent':
            remaining_pct = max(0.0, 100.0 - (self.line_first_payment_percentage or 0.0))
            inst_pct = remaining_pct / count
            return total * (inst_pct / 100.0)
        remaining = max(0.0, total - first_pay)
        return remaining / count

    def _is_installment_product_line(self):
        self.ensure_one()
        return not self.display_type

    @api.model_create_multi
    def create(self, vals_list):
        generate_flags = [
            any(
                field in vals
                for field in ('line_installment_count', 'line_first_payment_type', 'line_first_payment_percentage')
            )
            for vals in vals_list
        ]
        for vals in vals_list:
            self._sync_line_plan_values_from_term(vals)
        lines = super().create(vals_list)
        lines_to_generate = lines.filtered(lambda line: generate_flags[lines.ids.index(line.id)])
        lines_to_generate._generate_line_payment_terms_from_values()
        return lines

    def write(self, vals):
        vals = dict(vals)
        should_generate = any(
            field in vals
            for field in ('line_installment_count', 'line_first_payment_type', 'line_first_payment_percentage')
        )
        self._sync_line_plan_values_from_term(vals)
        result = super().write(vals)
        if not self.env.context.get('skip_sale_line_payment_term_generation') and should_generate:
            self._generate_line_payment_terms_from_values()
        if not self.env.context.get('skip_auto_generate_sale_payment_term') and (
            should_generate or 'payment_term_id' in vals
        ):
            self.mapped('order_id')._regenerate_installment_preview()
        if (
            should_generate
            and hasattr(self, '_recompute_price_from_installments')
            and not self.env.context.get('skip_recompute_price_from_installments')
            and not self.env.context.get('skip_auto_generate_sale_payment_term')
        ):
            self._recompute_price_from_installments()
        return result

    def _get_plan_values_from_payment_term(self, payment_term):
        """Derive line installment fields from a payment term (incl. custom schedules)."""
        if not payment_term or not payment_term.is_installment_term:
            return {}

        if payment_term.pay_type == 'custom':
            term_lines = payment_term.line_ids.sorted(key=lambda line: (line.nb_days, line.id))
            if not term_lines:
                return {
                    'line_installment_count': 0,
                    'line_first_payment_type': payment_term.first_payment_type or 'percent',
                    'line_first_payment_percentage': payment_term.first_payment_percentage or 0.0,
                }

            if payment_term.first_payment_percentage and payment_term.first_payment_percentage > 0:
                installment_lines = term_lines.filtered(lambda line: line.nb_days > 0)
                installment_count = len(installment_lines) or max(len(term_lines) - 1, 0)
                return {
                    'line_installment_count': installment_count,
                    'line_first_payment_type': payment_term.first_payment_type or 'percent',
                    'line_first_payment_percentage': payment_term.first_payment_percentage,
                }

            first_line = term_lines[0]
            if len(term_lines) > 1 and first_line.nb_days == 0:
                return {
                    'line_installment_count': len(term_lines) - 1,
                    'line_first_payment_type': first_line.value,
                    'line_first_payment_percentage': first_line.value_amount,
                }

            return {
                'line_installment_count': len(term_lines),
                'line_first_payment_type': 'percent',
                'line_first_payment_percentage': 0.0,
            }

        return {
            'line_installment_count': payment_term.installment_count or 0,
            'line_first_payment_type': payment_term.first_payment_type or 'fixed',
            'line_first_payment_percentage': payment_term.first_payment_percentage or 0.0,
        }

    def _apply_plan_values_from_payment_term(self, payment_term=None):
        payment_term = payment_term or self.payment_term_id
        plan_values = self._get_plan_values_from_payment_term(payment_term)
        if not plan_values:
            return
        for field in (
            'line_installment_count',
            'line_first_payment_type',
            'line_first_payment_percentage',
        ):
            if field in plan_values:
                setattr(self, field, plan_values[field])

    def _sync_line_plan_values_from_term(self, vals):
        if not vals.get('payment_term_id'):
            return
        payment_term = self.env['account.payment.term'].browse(vals['payment_term_id'])
        if not payment_term.exists():
            return
        plan_values = self._get_plan_values_from_payment_term(payment_term)
        for key, value in plan_values.items():
            vals.setdefault(key, value)

    def _get_base_order_payment_term(self):
        self.ensure_one()
        return self.order_id.payment_term_id

    def _get_line_payment_term_values(self):
        self.ensure_one()
        base_term = self._get_base_order_payment_term()
        return {
            'pay_type': (base_term.pay_type if base_term else False) or self.order_id.pay_type or 'fixed',
            'installment_count': self.line_installment_count,
            'first_payment_type': self.line_first_payment_type or (base_term.first_payment_type if base_term else 'fixed'),
            'first_payment_percentage': self.line_first_payment_percentage,
            'baseline_date': (base_term.baseline_date if base_term else False) or self.order_id.baseline_date or 'invoice_date',
            'settlement_trigger': (base_term.settlement_trigger if base_term else False) or self.order_id.settlement_trigger or 'cia',
            'installment_frequency': (
                base_term.installment_frequency
                if base_term and base_term.pay_type == 'fixed'
                else self.order_id.installment_frequency
            ) or 'monthly',
            'line_amount': self.price_total,
        }

    def _build_line_payment_term_commands(self, term_values):
        # Shared with account.move.line via installment.config.mixin so both build
        # the EXACT same per-line installment schedule. Logic unchanged.
        self.ensure_one()
        return self.env['installment.config.mixin']._build_installment_line_commands(term_values)

    def _payment_term_matches_line_values(self):
        self.ensure_one()
        term = self.payment_term_id
        if not term or not term.is_installment_term:
            return False
        expected = self._get_plan_values_from_payment_term(term)
        return (
            self.line_installment_count == expected.get('line_installment_count', 0)
            and self.line_first_payment_type == expected.get('line_first_payment_type')
            and self.line_first_payment_percentage == expected.get('line_first_payment_percentage', 0.0)
        )

    def _generate_line_payment_terms_from_values(self):
        PaymentTerm = self.env['account.payment.term']
        for line in self.filtered(
            lambda item: item.order_id.apply_payment_term_per_line and item._is_installment_product_line()
        ):
            if line.order_id.state not in ('draft', 'sent'):
                continue
            if line._payment_term_matches_line_values():
                continue
            base_term = line._get_base_order_payment_term()
            term_values = line._get_line_payment_term_values()
            term_vals = {
                'company_id': line.company_id.id,
                'is_installment_term': True,
                'pay_type': term_values['pay_type'],
                'installment_count': term_values['installment_count'],
                'first_payment_type': term_values['first_payment_type'],
                'first_payment_percentage': term_values['first_payment_percentage'],
                'baseline_date': term_values['baseline_date'],
                'settlement_trigger': term_values['settlement_trigger'],
                'scope': 'per_lines',
                'installment_frequency': term_values['installment_frequency'],
                'line_ids': line._build_line_payment_term_commands(term_values),
            }
            term_preview = PaymentTerm.new(term_vals)
            term_vals['name'] = term_preview._generate_auto_name() or _(
                "Line Installments - %s"
            ) % (line.name or line.order_id.name or _("Sale Order Line"))
            if base_term:
                term_vals['name'] = _("%s - %s") % (base_term.name, line.name or _("Sale Order Line"))
            term = PaymentTerm.create(term_vals)
            line.with_context(skip_sale_line_payment_term_generation=True).payment_term_id = term

    @api.onchange('payment_term_id')
    def _onchange_payment_term_id(self):
        if self.payment_term_id:
            self._apply_plan_values_from_payment_term(self.payment_term_id)
        if self.order_id and self.order_id.apply_payment_term_per_line:
            self.order_id._regenerate_installment_preview()

    @api.onchange('line_installment_count', 'line_first_payment_type', 'line_first_payment_percentage')
    def _onchange_line_payment_term_values(self):
        for line in self:
            if line.payment_term_id and not line._payment_term_matches_line_values():
                line.payment_term_id = False
        if hasattr(self, '_recompute_price_from_installments'):
            self._recompute_price_from_installments()
        if self.order_id and self.order_id.apply_payment_term_per_line:
            self.order_id._regenerate_installment_preview()

    def _prepare_invoice_line(self, **optional_values):
        vals = super()._prepare_invoice_line(**optional_values)
        if self.order_id.apply_payment_term_per_line:
            if self.payment_term_id:
                vals['payment_term_id'] = self.payment_term_id.id
            vals['line_installment_count'] = self.line_installment_count
            vals['line_first_payment_type'] = self.line_first_payment_type
            vals['line_first_payment_percentage'] = self.line_first_payment_percentage
        return vals