import requests
import datetime
from odoo import fields, models, api, _
from odoo.exceptions import UserError
import logging
import time
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)

class FoodicsConnector(models.Model):
    _name = 'foodics.connector'
    _rec_name = 'business_name'
    _description = "Foodics Connector"

    business_name = fields.Char(string='Business', readonly=True)
    user_name = fields.Char(string='User', readonly=True, copy=False)
    email = fields.Char(readonly=True, copy=False)
    order_date = fields.Date()
    access_token = fields.Char(string='Access Token', required=True)

    from_date = fields.Date(string='Last POS Order Imported Date')
    last_purchase_order_import_date = fields.Date(string='Last Purchase Order Imported Date')
    to_date = fields.Date(string='To Date')
    state = fields.Selection([('authenticate', 'Authenticate'), ('authenticated', 'Authenticated')], default='authenticate',copy=False)
    page = fields.Integer(default=1)
    note = fields.Text()
    environment = fields.Selection([('sandbox', 'Sandbox'), ('production', 'Production')], required=True, default='production')
    url = fields.Char(compute='set_foodics_url')
    product_timestamp = fields.Char(default='2000-01-01 01:01:01')
    current_product_page = fields.Integer(default=1)
    current_product_timestamp = fields.Char(default='2000-01-01 01:01:01')
    # Orders resume controls
    orders_selected_date = fields.Char(string='Orders Selected Date', default=False, copy=False)
    orders_next_page = fields.Integer(string='Orders Next Page', default=1, copy=False)

    @api.depends('environment')
    def set_foodics_url(self):
        for rec in self:
            if rec.environment == 'sandbox':
                rec.url = 'https://api-sandbox.foodics.com'
            else:
                rec.url = 'https://api.foodics.com'

    def foodics_whoami(self):
        res = self.foodic_import_data(self.url + '/v5/whoami')
        self.business_name = res.get('data').get('business').get('name')
        self.user_name = res.get('data').get('user').get('name')
        self.email = res.get('data').get('user').get('email')
        self.state = 'authenticated'

    def authenticate(self):
        self.foodics_whoami()
        # console = 'console-sandbox' if self.environment == 'sandbox' else 'console'
        # target_url = 'https://%s.foodics.com/authorize?client_id=%s&state=%s' % (console, self.client_id, self.id)
        # return {
        #     'type': 'ir.actions.act_url',
        #     'target': 'self',
        #     'url': target_url,
        # }

    def foodic_import_data(self, url, *, timeout_connect=10, timeout_read=60, max_retries=5, backoff_base=1.5):
        access_token = self.access_token
        headers = {
            'authorization': "Bearer %s" % access_token,
            'content-type': 'text/plain',
        }
        attempt = 0
        last_exc = None
        while attempt < max_retries:
            try:
                response = requests.get(url, headers=headers, timeout=(timeout_connect, timeout_read))
                # Success
                if response.status_code == 200:
                    return response.json()
                # Too Many Requests: respect Retry-After if provided
                if response.status_code == 429:
                    retry_after = response.headers.get('Retry-After')
                    sleep_secs = 0
                    if retry_after:
                        try:
                            sleep_secs = int(retry_after)
                        except Exception:
                            sleep_secs = int(backoff_base ** attempt)
                    else:
                        sleep_secs = int(backoff_base ** attempt)
                    time.sleep(min(sleep_secs, 120))
                # Transient server/network errors – retry
                elif response.status_code in (500, 502, 503, 504):
                    time.sleep(min(int(backoff_base ** attempt), 60))
                else:
                    # Client errors or unexpected codes: do not spin forever
                    try:
                        detail = response.json()
                    except Exception:
                        detail = response.text
                    raise UserError(_('Foodics API error: %s (%s)') % (response.status_code, detail))
            except requests.exceptions.Timeout as e:
                last_exc = e
                time.sleep(min(int(backoff_base ** attempt), 60))
            except requests.exceptions.RequestException as e:
                last_exc = e
                time.sleep(min(int(backoff_base ** attempt), 60))
            attempt += 1
        if last_exc:
            raise UserError(_('Connection to Foodics failed after retries: %s') % last_exc)
        raise UserError(_('Something Went Wrong !'))

    def success_popup(self, data):
        return {
            "name": "Message",
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "pop.message",
            "target": "new",
            "context": {
                "default_name": "Successfully %s Imported!"%data
            },
        }

    def get_branches(self):
        data_access_url = self.url + '/v5/branches'
        res = self.foodic_import_data(data_access_url)
        Branch = self.env['pos.config']
        Branch.set_branches_to_odoo(res)
        last_page = int(res.get('meta').get('last_page'))
        if last_page > 1:
            for page_no in range(int(res.get('meta').get('current_page')) + 1, last_page + 1):
                res = self.foodic_import_data(data_access_url + "?page={}".format(page_no))
                Branch.set_branches_to_odoo(res)
        return self.success_popup('Branches')

    def get_payment_methods(self):
        data_access_url = self.url + '/v5/payment_methods'
        res = self.foodic_import_data(data_access_url)
        PaymentMethods = self.env['pos.payment.method']
        PaymentMethods.set_payment_methods_to_odoo(res)
        last_page = int(res.get('meta').get('last_page'))
        if last_page > 1:
            for page_no in range(int(res.get('meta').get('current_page')) + 1, last_page + 1):
                res = self.foodic_import_data(data_access_url + "?page={}".format(page_no))
                PaymentMethods.set_payment_methods_to_odoo(res)
        return self.success_popup('Payment Methods')

    def get_categories_methods(self):
        data_access_url = self.url + '/v5/categories'
        res = self.foodic_import_data(data_access_url)
        PosCategory = self.env['pos.category']
        PosCategory.set_categories_to_odoo(res)
        last_page = int(res.get('meta').get('last_page'))
        if last_page > 1:
            for page_no in range(int(res.get('meta').get('current_page')) + 1, last_page + 1):
                res = self.foodic_import_data(data_access_url + "?page={}".format(page_no))
                PosCategory.set_categories_to_odoo(res)
        return self.success_popup('Categories')


    def get_products_methods(self):
        log = self.env['foodics.sync.log'].create({
            'connector_id': self.id,
            'job_type': 'products',
            'status': 'running',
        })
        try:
            data_access_url = self.url + '/v5/products?filter[updated_after]=%s' % self.product_timestamp
            res = self.foodic_import_data(data_access_url)
            Product = self.env['product.product']
            self.current_product_timestamp = Product.set_products_to_odoo(res, self.current_product_timestamp)
            last_page = int(res.get('meta').get('last_page'))
            log.write({'page_total': last_page})
            page = self.current_product_page if self.current_product_page != 1 else int(res.get('meta').get('current_page')) + 1
            if last_page > 1:
                for page_no in range(page, last_page + 1):
                    res = self.foodic_import_data(data_access_url + "&page={}".format(page_no))
                    self.current_product_timestamp = Product.set_products_to_odoo(res, self.current_product_timestamp)
                    self.current_product_page = page_no
                    log.write({'page_current': page_no, 'items_processed': (log.items_processed or 0) + len(res.get('data', []))})
                    self._cr.commit()
                self.product_timestamp = self.current_product_timestamp
                self.current_product_page = 1
                self._cr.commit()
            log.mark_success()
        except Exception as e:
            log.mark_failed(str(e))
            raise

    def foodics_import_purchase_orders(self):
        data_access_url = self.url + '/v5/purchase_orders?include=supplier,items,branch'
        res = self.foodic_import_data(data_access_url)
        purchase_order = self.env['purchase.order']
        purchase_order.set_orders_to_odoo(res)
        last_page = int(res.get('meta').get('last_page'))
        if last_page > 1:
            for page_no in range(int(res.get('meta').get('current_page')) + 1, last_page + 1):
                res = self.foodic_import_data(data_access_url + "&page={}".format(page_no))
                purchase_order.set_orders_to_odoo(res)

    def get_orders_methods(self, from_date=None, limit_count=None, shift=None):
        log = self.env['foodics.sync.log'].create({
            'connector_id': self.id,
            'job_type': 'orders',
            'status': 'running',
        })
        try:
            # Enforce a hard cap to keep UI responsive
            # If called from wizard and no explicit limit, apply an internal safe cap
            if self.env.context.get('from_wizard') and not limit_count:
                limit_count = 150
            if limit_count and limit_count > 200:
                limit_count = 200
            if not from_date and not self.from_date:
                from_date_str = (datetime.datetime.now() - relativedelta(years=1000)).date().strftime('%Y-%m-%d')
            elif from_date:
                # Use the exact selected day; no previous-day shift
                from_date_str = from_date.strftime('%Y-%m-%d')
            else:
                # self.from_date is a Date field -> convert to string
                from_date_str = self.from_date.strftime('%Y-%m-%d')
            # store back (Odoo Date will accept string)
            self.from_date = from_date_str
            # Resume logic: if same selected date, start from saved next page; otherwise reset to 1
            if self.env.context.get('from_wizard'):
                if self.orders_selected_date == from_date_str and self.orders_next_page and self.orders_next_page > 1:
                    self.page = self.orders_next_page
                else:
                    self.page = 1
                    self.orders_selected_date = from_date_str
                    self.orders_next_page = 1

            # Compute shift window if provided (localized to user/company timezone)
            shift_from_dt = None
            shift_to_dt = None
            tz_name = self.env.user.tz or self.env.company.partner_id.tz or 'UTC'
            # Shift time ranges (00-08, 08-16, 16-24)
            try:
                base_date = datetime.datetime.strptime(from_date_str, '%Y-%m-%d').date()
            except Exception:
                base_date = datetime.datetime.now().date()
            if shift == 'shift_1':
                shift_from_dt = datetime.datetime.combine(base_date, datetime.time(0, 0, 0))
                shift_to_dt = datetime.datetime.combine(base_date, datetime.time(8, 0, 0))
            elif shift == 'shift_2':
                shift_from_dt = datetime.datetime.combine(base_date, datetime.time(8, 0, 0))
                shift_to_dt = datetime.datetime.combine(base_date, datetime.time(16, 0, 0))
            elif shift == 'shift_3':
                shift_from_dt = datetime.datetime.combine(base_date, datetime.time(16, 0, 0))
                shift_to_dt = datetime.datetime.combine(base_date + datetime.timedelta(days=1), datetime.time(0, 0, 0))

            # API filters are date-based; we narrow time inside set_orders_to_odoo
            to_date = (base_date + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
            # Log precise datetime window if shift used
            if shift_from_dt and shift_to_dt:
                log.write({'from_date': "%s (%s)" % (shift_from_dt.strftime('%Y-%m-%d %H:%M:%S'), tz_name),
                           'to_date': "%s (%s)" % (shift_to_dt.strftime('%Y-%m-%d %H:%M:%S'), tz_name)})
            else:
                # When running by exact business_date, show the same date in both fields for clarity
                log.write({'from_date': from_date_str, 'to_date': from_date_str})
            # Build URL: if running by a single date (no shift), use exact business_date to avoid window edge cases
            base_include = "include=branch,charges.charge,charges.taxes,discount,customer,products.product,payments,payments.paymentMethod,products.taxes,creator,products.options.modifierOption"
            if shift:
                url = self.url + f"/v5/orders?{base_include}&sort=reference&page={{}}&filter[business_date_after]={{}}&filter[business_date_before]={{}}"
                first_url = url.format(self.page, from_date_str, to_date)
            else:
                url = self.url + f"/v5/orders?{base_include}&sort=reference&page={{}}&filter[business_date]={{}}"
                first_url = url.format(self.page, from_date_str)
            res = self.foodic_import_data(first_url)

            Order = self.env['pos.order']
            received = len(res.get('data', []) or [])
            processed = Order.set_orders_to_odoo(res, to_date, shift_from_dt, shift_to_dt) or 0
            meta = res.get('meta', {}) or {}
            # Try to compute an accurate total for the date range
            total_orders = meta.get('total')
            if total_orders is None:
                try:
                    per_page = meta.get('per_page') or len(res.get('data', [])) or 0
                    last_page = meta.get('last_page') or 1
                    total_orders = per_page * last_page if per_page else None
                except Exception:
                    total_orders = None
            if total_orders is not None:
                log.write({'total_expected': int(total_orders)})
            log.write({'items_received': received, 'items_processed': (log.items_processed or 0) + processed, 'query_url': first_url})
            # If we already reached the limit on the first page, stop early and inform the user
            if limit_count and processed >= limit_count:
                remaining_estimate = max((total_orders - processed), 0) if total_orders is not None else 'غير معلوم'
                log.mark_success()
                return {
                    "name": "Message",
                    "type": "ir.actions.act_window",
                    "view_type": "form",
                    "view_mode": "form",
                    "res_model": "pop.message",
                    "target": "new",
                    "context": {
                        "default_name": "تم تنزيل %s طلب حتى الآن خلال الفترة %s → %s، والمتبقي %s طلب سيتم استكماله لاحقًا." % (processed, from_date_str, to_date, remaining_estimate)
                    },
                }
            if res and res.get('meta', {}):
                last_page = int(res.get('meta').get('last_page'))
                current_page = int(res.get('meta').get('current_page'))
                # If our starting page is out of range (e.g., 131 > 1), snap to 1 and refetch
                if current_page > last_page:
                    self.page = 1
                    refetch_url = url.format(self.page, from_date_str, to_date) if shift else url.format(self.page, from_date_str)
                    res = self.foodic_import_data(refetch_url)
                    received = len(res.get('data', []) or [])
                    processed = Order.set_orders_to_odoo(res, to_date, shift_from_dt, shift_to_dt) or 0
                    meta = res.get('meta', {}) or {}
                    last_page = int(meta.get('last_page') or 1)
                    current_page = int(meta.get('current_page') or 1)
                    log.write({'items_received': received, 'items_processed': (log.items_processed or 0) + processed, 'query_url': refetch_url})
                log.write({'page_total': last_page, 'page_current': current_page, 'items_processed': (log.items_processed or 0) + processed})
                if last_page > 1:
                    for page_no in range(current_page + 1, last_page + 1):
                        if page_no % 30 == 0:
                            time.sleep(60)
                        page_url = url.format(page_no, from_date_str, to_date) if shift else url.format(page_no, from_date_str)
                        res = self.foodic_import_data(page_url)
                        self.page = page_no
                        # Persist resume position (next page)
                        try:
                            self.orders_selected_date = from_date_str
                            self.orders_next_page = page_no + 1
                            self._cr.commit()
                        except Exception:
                            pass
                        received = len(res.get('data', []) or [])
                        batch_count = Order.set_orders_to_odoo(res, to_date, shift_from_dt, shift_to_dt) or 0
                        processed += batch_count
                        log.write({'page_current': page_no, 'items_received': (log.items_received or 0) + received, 'items_processed': (log.items_processed or 0) + batch_count, 'query_url': page_url})
                        if limit_count and processed >= limit_count:
                            # Stop early; keep self.page at current so next run resumes
                            # Remaining based on accurate meta total if available; fallback to page estimate
                            if total_orders is not None:
                                remaining_estimate = max(total_orders - processed, 0)
                                log.write({'total_expected': int(total_orders)})
                            else:
                                try:
                                    remaining_pages = last_page - page_no
                                    per_page_est = (meta.get('per_page') or 0)
                                    remaining_estimate = remaining_pages * per_page_est if per_page_est > 0 else 'غير معلوم'
                                except Exception:
                                    remaining_estimate = 'غير معلوم'
                            log.mark_success()
                            return {
                                "name": "Message",
                                "type": "ir.actions.act_window",
                                "view_type": "form",
                                "view_mode": "form",
                                "res_model": "pop.message",
                                "target": "new",
                                "context": {
                                    "default_name": "Downloaded %s orders for %s → %s. Remaining (estimate): %s. The next run will resume from the next page." % (processed, from_date_str, to_date, remaining_estimate)
                                },
                            }
                    # Finished all pages: reset resume to 1
                    self.page = 1
                    self.orders_next_page = 1
            # Final summary popup with counts
            remaining_final = None
            try:
                remaining_final = max((total_orders - processed), 0) if total_orders is not None else None
            except Exception:
                remaining_final = None
            log.mark_success()
            summary = "Downloaded %s orders in this run for %s," % (processed, from_date_str)
            if total_orders is not None:
                summary += " total in Foodics: %s, remaining: %s." % (int(total_orders), int(remaining_final or 0))
            else:
                summary += " and could not read the total from Foodics."
            return {
                "name": "Message",
                "type": "ir.actions.act_window",
                "view_type": "form",
                "view_mode": "form",
                "res_model": "pop.message",
                "target": "new",
                "context": {
                    "default_name": summary
                },
            }
        except Exception as e:
            log.mark_failed(str(e))
            raise

    def get_specific_orders(self, order_references):
        url = self.url + "/v5/orders?include=tags,branch,charges.charge,charges.taxes,discount,customer,products.product,payments,payments.paymentMethod,products.taxes,creator,products.options.modifierOption,combos.combo_size,combos.products.product,combos.products.options,combos.products.taxes,combos.products.options.modifierOption&sort=reference&page={}&filter[reference]={}".format(1, order_references)
        res = self.foodic_import_data(url)
        Order = self.env['pos.order']
        Order.set_orders_to_odoo(res)
        if res and res.get('meta', {}):
            last_page = int(res.get('meta').get('last_page'))
            current_page = int(res.get('meta').get('current_page'))
            if last_page > 1:
                for page_no in range(current_page + 1, last_page + 1):
                    if page_no % 30 == 0:
                        time.sleep(60)
                    res = self.foodic_import_data(url.format(page_no, order_references))
                    Order.set_orders_to_odoo(res)


    def cron_sync_pos_order(self):
        for connector in self.search([('state', '=', 'authenticated')]):
            connector.get_orders_methods()

    def cron_sync_products(self):
        for connector in self.search([('state', '=', 'authenticated')]):
            connector.get_products_methods()
