from odoo import fields , models , api , _
from ast import literal_eval
from odoo.exceptions import ValidationError
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime, timedelta

class ResConfigSettings(models.TransientModel):
	_inherit = "res.config.settings"
	_description="Res config Settings"


	
	start_notification=fields.Boolean(string='Delay Task Start Notification',default=False)
	delay_notification=fields.Boolean(string='Delay Task Deadline/Overdue Notification',default=False)
	start_count=fields.Integer(string='Delay Day(s)',default=0)
	delay_count=fields.Integer(string='Delay Deadline Day(s)',default=0)
	done_stage_ckecklist = fields.Many2one('project.task.type','Done Stage')
	todo_stage_ckecklist = fields.Many2one('project.task.type','To Do Stage')
	cancel_stage_ckecklist = fields.Many2one('project.task.type','Cancel Stage')
	warning_child_task = fields.Many2one('project.task.type', 'Prevent stage to change untill all task on same stage')

	first_reminder = fields.Float(string='First Reminder(Days)')
	second_reminder = fields.Float(string='Second Reminder(Days)')
	first_date = fields.Date(compute='convert_first_date')
	second_date = fields.Date(compute='convert_second_date')
	allow_multi_task = fields.Boolean(string='Allow Multi Task')

	def validate_date(self):
		if self.first_reminder > self.second_reminder:
			return True
		else:
			raise UserError(_('First Reminder(Days) should be greater than Second Reminder(Days)'))
		return False


	@api.model
	def get_values(self):
		res = super(ResConfigSettings, self).get_values()
		start_notification = self.env["ir.config_parameter"].sudo().get_param("bi_all_in_one_project_management_system.start_notification")
		delay_notification = self.env["ir.config_parameter"].sudo().get_param("bi_all_in_one_project_management_system.delay_notification")
		start_count = self.env["ir.config_parameter"].sudo().get_param("bi_all_in_one_project_management_system.start_count")
		delay_count = self.env["ir.config_parameter"].sudo().get_param("bi_all_in_one_project_management_system.delay_count")
		first_reminder = self.env['ir.config_parameter'].sudo().get_param('bi_all_in_one_project_management_system.first_reminder')
		second_reminder = self.env['ir.config_parameter'].sudo().get_param('bi_all_in_one_project_management_system.second_reminder')
		first_date = self.env['ir.config_parameter'].sudo().get_param('bi_all_in_one_project_management_system.first_date')
		second_date = self.env['ir.config_parameter'].sudo().get_param('bi_all_in_one_project_management_system.second_date')
		todo_stage_ckecklist = self.env['ir.config_parameter'].sudo().get_param('bi_all_in_one_project_management_system.todo_stage_ckecklist')
		done_stage_ckecklist = self.env['ir.config_parameter'].sudo().get_param('bi_all_in_one_project_management_system.done_stage_ckecklist')
		cancel_stage_ckecklist = self.env['ir.config_parameter'].sudo().get_param('bi_all_in_one_project_management_system.cancel_stage_ckecklist')
		warning_child_task = self.env['ir.config_parameter'].sudo().get_param('bi_all_in_one_project_management_system.warning_child_task')
		allow_multi_task = self.env["ir.config_parameter"].sudo().get_param("bi_all_in_one_project_management_system.allow_multi_task")
		
		res.update(
			start_notification=start_notification,
			delay_notification=delay_notification,
			start_count =literal_eval(str(start_count)),
			delay_count = literal_eval(str(delay_count)),
			first_reminder = float(first_reminder),
			second_reminder = float(second_reminder),
			first_date = first_date,
			second_date = second_date,
			todo_stage_ckecklist=literal_eval(str(todo_stage_ckecklist)),
			done_stage_ckecklist=literal_eval(str(done_stage_ckecklist)),
			cancel_stage_ckecklist=literal_eval(str(cancel_stage_ckecklist)),
			warning_child_task=literal_eval(str(warning_child_task)),
			allow_multi_task=allow_multi_task
		)
		return res

	def set_values(self):
		res = super(ResConfigSettings, self).set_values()
		config_env=self.env['ir.config_parameter'].sudo()
		config_env.set_param("bi_all_in_one_project_management_system.start_notification", self.start_notification)
		config_env.set_param("bi_all_in_one_project_management_system.delay_notification", self.delay_notification)
		config_env.set_param("bi_all_in_one_project_management_system.start_count", self.start_count)
		config_env.set_param("bi_all_in_one_project_management_system.delay_count",self.delay_count)
		config_env.set_param('bi_all_in_one_project_management_system.first_reminder', self.first_reminder)
		config_env.set_param('bi_all_in_one_project_management_system.second_reminder', self.second_reminder)
		config_env.set_param('bi_all_in_one_project_management_system.first_date', self.first_date)
		config_env.set_param('bi_all_in_one_project_management_system.second_date', self.second_date)	
		config_env.set_param('bi_all_in_one_project_management_system.todo_stage_ckecklist', self.todo_stage_ckecklist.id)	
		config_env.set_param('bi_all_in_one_project_management_system.done_stage_ckecklist', self.done_stage_ckecklist.id)	
		config_env.set_param('bi_all_in_one_project_management_system.cancel_stage_ckecklist', self.cancel_stage_ckecklist.id)	
		config_env.set_param('bi_all_in_one_project_management_system.warning_child_task', self.warning_child_task.id)	
		config_env.set_param('bi_all_in_one_project_management_system.allow_multi_task', self.allow_multi_task)	


	@api.onchange('first_reminder')
	def convert_first_date(self):
		self.first_date = None
		for tasks in self.env['project.task'].search([]):
			if tasks.date_deadline !=False:
				reminder_date = datetime.strptime(tasks.date_deadline.strftime("%Y/%m/%d %H:%M:%S"),"%Y/%m/%d %H:%M:%S")
				first = reminder_date - timedelta(days=self.first_reminder)
				then = datetime.strptime(str(first), '%Y-%m-%d %H:%M:%S').date()
				today = datetime.now().date()
				if then == today:
					self.first_date = then


	@api.onchange('second_reminder')
	def convert_second_date(self):
		self.second_date = None
		for proj_task in self.env['project.task'].search([]):
			if proj_task.date_deadline !=False:
				reminders_date = datetime.strptime(proj_task.date_deadline.strftime("%Y/%m/%d %H:%M:%S"),"%Y/%m/%d %H:%M:%S")
				second = reminders_date - timedelta(days=self.second_reminder)
				now = datetime.strptime(str(second), '%Y-%m-%d %H:%M:%S').date()
				today = datetime.now().date()
				if now == today:
					self.second_date = now