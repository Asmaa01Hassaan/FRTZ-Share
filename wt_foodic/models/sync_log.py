from odoo import models, fields, api


class FoodicsSyncLog(models.Model):
	_name = 'foodics.sync.log'
	_description = 'Foodics Sync Log'
	_order = 'create_date desc'

	connector_id = fields.Many2one('foodics.connector', ondelete='set null')
	job_type = fields.Selection([
		('branches', 'Branches'),
		('payment_methods', 'Payment Methods'),
		('categories', 'Categories'),
		('products', 'Products'),
		('orders', 'Orders'),
		('purchase_orders', 'Purchase Orders'),
	], required=True)
	status = fields.Selection([
		('running', 'Running'),
		('success', 'Success'),
		('failed', 'Failed'),
	], default='running', required=True)
	start_time = fields.Datetime(default=lambda self: fields.Datetime.now())
	end_time = fields.Datetime()
	page_current = fields.Integer()
	page_total = fields.Integer()
	items_processed = fields.Integer(string='Pulled')
	total_expected = fields.Integer(string='Total (Foodics)')
	remaining_count = fields.Integer(string='Remaining', compute='_compute_remaining', store=False)
	error_message = fields.Text()
	from_date = fields.Char()
	to_date = fields.Char()
	query_url = fields.Char()
	items_received = fields.Integer(string='Received')

	def mark_success(self):
		self.write({'status': 'success', 'end_time': fields.Datetime.now()})

	def mark_failed(self, message):
		self.write({'status': 'failed', 'end_time': fields.Datetime.now(), 'error_message': message})

	@api.depends('items_processed', 'total_expected')
	def _compute_remaining(self):
		for rec in self:
			if rec.total_expected and rec.total_expected >= 0:
				rec.remaining_count = max(rec.total_expected - (rec.items_processed or 0), 0)
			else:
				rec.remaining_count = 0

