from odoo import http
from odoo.http import request


class PortalDashboard(http.Controller):

    @http.route(['/my/portal-dashboard', '/my/portal-dashboard/<string:page>'], type='http', auth='user', website=True)
    def portal_dashboard(self, page='index', **kw):
        values = {
            'active_page': page,
        }
        if page == 'project_hub':
            projects = request.env['project.project'].search([])
            values.update({
                'projects': projects,
            })
        return request.render('project_portal_management.my_custom_dashboard', values)


    @http.route('/my/project/create/save', type='http', auth='user', methods=['POST'], website=True)
    def portal_project_save(self, **post):
        tag_ids = request.httprequest.form.getlist('tag_ids')

        tag_ids = [int(tid) for tid in tag_ids] if tag_ids else []
        request.env['project.project'].create({
            'name': post.get('name'),
            'partner_id': int(post.get('partner_id')) if post.get('partner_id') else False,
            'user_id': int(post.get('user_id')) if post.get('user_id') else request.env.user.id,
            'date_start': post.get('date_start') or False,
            'date': post.get('date') or False,
            'tag_ids': [(6, 0, tag_ids)] if tag_ids else False,
            'label_tasks': post.get('label_tasks') or False,

        })
        return request.redirect('/my/portal-dashboard/project_hub')

    @http.route('/my/project/update/save', type='http', auth='user', methods=['POST'], website=True)
    def portal_project_update(self, **post):
        project_id = post.get('project_id')
        if project_id:
            project = request.env['project.project'].browse(int(project_id))
            if project.exists():
                tag_ids = request.httprequest.form.getlist('tag_ids')
                tag_list = [(6, 0, [int(tid) for tid in tag_ids])] if tag_ids else [(5, 0, 0)]

                project.write({
                    'name': post.get('name'),
                    'partner_id': int(post.get('partner_id')) if post.get('partner_id') else False,
                    'user_id': int(post.get('user_id')) if post.get('user_id') else request.env.user.id,
                    'date_start': post.get('date_start') or False,
                    'date': post.get('date') or False,
                    'label_tasks': post.get('label_tasks') or False,
                    'tag_ids': tag_list,
                })
        return request.redirect('/my/portal-dashboard/project_hub')

    @http.route('/my/project/delete', type='http', auth='user', methods=['POST'], website=True)
    def portal_project_delete(self, **post):

        project_id = post.get('project_id')
        if project_id:
            project = request.env['project.project'].browse(int(project_id))
            if project.exists():
                project.unlink()

        return request.redirect('/my/portal-dashboard/project_hub')



    @http.route('/my/task/create/save', type='http', auth='user', methods=['POST'], website=True)
    def portal_task_save(self, **post):
        if post.get('name') and post.get('project_id'):
            description = post.get('description', '').replace('\n', '<br/>')

            request.env['project.task'].create({
                'name': post.get('name'),
                'project_id': int(post.get('project_id')),
                'priority': post.get('priority', '0'),
                'date_deadline': post.get('date_deadline') if post.get('date_deadline') else False,
                'user_ids': [(4, int(post.get('user_ids')))] if post.get('user_ids') else False,
                'description': f"<div>{description}</div>",
            })
        return request.redirect('/my/portal-dashboard/project_hub')


    @http.route('/my/project/view/<int:project_id>', type='http', auth='user', website=True)
    def portal_project_view(self, project_id, **kw):
        project = request.env['project.project'].browse(project_id)
        if not project.exists():
            return request.redirect('/my/portal-dashboard/project_hub')

        return request.render('project_portal_management.template_project_view', {
            'project': project,
        })

    @http.route('/my/invoice/create', type='http', auth='user', website=True)
    def portal_create_invoice(self, project_id=None, **kw):

        project = request.env['project.project'].browse(int(project_id))

        values = {
            'project': project,
            'partner': project.partner_id,
        }

        return request.render('project_portal_management.template_invoice_create', values)



    @http.route('/my/invoice/create/save', type='http', auth='user', methods=['POST'], website=True)
    def portal_invoice_create_save(self, **post):

        project = request.env['project.project'].browse(int(post.get('project_id')))

        journal = request.env['account.journal'].search([
            ('type', '=', 'sale')
        ], limit=1)

        product = request.env['product.product'].search([], limit=1)

        invoice = request.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': project.partner_id.id,
            'journal_id': journal.id,
            'invoice_origin': project.name,
            'invoice_date': post.get('invoice_date'),
            'invoice_date_due': post.get('invoice_date_due'),
            'ref': post.get('ref'),
            'narration': post.get('narration'),
            'invoice_line_ids': [(0, 0, {
                'product_id': product.id,
                'name': project.name,
                'quantity': 1,
                'price_unit': float(post.get('amount', 0)),
            })]
        })

        return request.redirect('/my/project/view/%s' % project.id)

    @http.route('/my/project/invoices', type='http', auth='user', website=True)
    def portal_project_invoices(self, project_id=None, **kw):
        if not project_id:
            return request.redirect('/my/projects')

        project = request.env['project.project'].browse(int(project_id))

        invoices = request.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('invoice_origin', '=', project.name)
        ])

        if not invoices:
            return request.redirect('/my/invoice/create?project_id=%s' % project.id)
        return request.render('project_portal_management.template_project_invoices', {
            'project': project,
            'invoices': invoices,
        })



    #sale order

    @http.route('/my/sale_order/create', type='http', auth='user', website=True)
    def portal_sale_order_create(self, project_id=None, **kw):
        project = request.env['project.project'].browse(int(project_id))
        return request.render('project_portal_management.template_sale_order_create', {
            'project': project,
            'partner': project.partner_id,
        })

    @http.route('/my/sale_order/create/save', type='http', auth='user', methods=['POST'], website=True)
    def portal_sale_order_create_save(self, **post):
        project_id = int(post.get('project_id'))
        project = request.env['project.project'].browse(project_id)
        product = request.env['product.product'].search([], limit=1)

        sale_order = request.env['sale.order'].create({
            'partner_id': project.partner_id.id,
            'origin': project.name,
            'client_order_ref': post.get('ref'),
            'note': post.get('note'),
            'project_id': project.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'name': post.get('description') or project.name,
                'product_uom_qty': 1,
                'price_unit': float(post.get('amount', 0)),
            })]
        })
        return request.redirect('/my/project/sale_orders?project_id=%s' % project.id)

    @http.route('/my/project/sale_orders', type='http', auth='user', website=True)
    def portal_project_sale_orders(self, project_id=None, **kw):
        if not project_id:
            return request.redirect('/my/projects')

        project = request.env['project.project'].browse(int(project_id))

        sale_orders = request.env['sale.order'].search([
            ('origin', '=', project.name)
        ])

        return request.render('project_portal_management.template_project_sale_orders', {
            'project': project,
            'sale_orders': sale_orders,
        })