# -*- coding: utf-8 -*-

from odoo import models, fields, api
import base64
import io
import logging

_logger = logging.getLogger(__name__)

try:
    from PIL import Image
    from pdf2image import convert_from_bytes
    PDF_TO_IMAGE_AVAILABLE = True
except ImportError:
    PDF_TO_IMAGE_AVAILABLE = False
    _logger.warning('pdf2image or PIL not available. Install with: pip install pdf2image pillow')

try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False
    _logger.warning('qrcode library not available. Install with: pip install qrcode[pil]')

try:
    from barcode import Code128
    from barcode.writer import ImageWriter
    BARCODE_AVAILABLE = True
except ImportError:
    BARCODE_AVAILABLE = False
    _logger.warning('barcode library not available. Install with: pip install python-barcode[images]')


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    whatsapp_invitation_status = fields.Selection(
        [
            ('not_sent', 'Not Sent'),
            ('sent', 'Sent'),
            ('failed', 'Failed'),
        ],
        string='WhatsApp Invitation Status',
        default='not_sent',
        tracking=True,
    )
    whatsapp_invitation_sent_date = fields.Datetime(
        string='WhatsApp Invitation Sent',
        tracking=True,
    )
    whatsapp_invitation_error = fields.Text(
        string='WhatsApp Error',
    )
    whatsapp_message_id = fields.Char(
        string='WhatsApp Message ID',
    )
    
    guest_id = fields.Many2one(
        'event.guest',
        string='Guest',
        help='Guest that this registration was created from',
        ondelete='set null'
    )
    
    badge_image = fields.Binary(
        string='Badge Image',
        attachment=True,
        help='Badge image generated from PDF badge'
    )
    
    badge_image_filename = fields.Char(
        string='Badge Image Filename',
        help='Filename of the badge image'
    )
    
    barcode_qr_image = fields.Binary(
        string='Barcode QR Code',
        compute='_compute_barcode_qr_image',
        store=False,
        help='QR Code image generated from barcode'
    )
    
    barcode_image = fields.Binary(
        string='Barcode Image',
        compute='_compute_barcode_image',
        store=False,
        help='Barcode image generated from barcode number'
    )
    
    @api.depends('barcode')
    def _compute_barcode_qr_image(self):
        """Generate QR code image from barcode"""
        for record in self:
            if record.barcode and QRCODE_AVAILABLE:
                try:
                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_M,
                        box_size=10,
                        border=4,
                    )
                    qr.add_data(record.barcode)
                    qr.make(fit=True)
                    
                    img = qr.make_image(fill_color="black", back_color="white")
                    
                    # Convert PIL image to base64
                    buffer = io.BytesIO()
                    img.save(buffer, format='PNG')
                    record.barcode_qr_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
                except Exception as e:
                    _logger.error(f'Error generating QR code: {str(e)}')
                    record.barcode_qr_image = False
            else:
                record.barcode_qr_image = False
    
    @api.depends('barcode')
    def _compute_barcode_image(self):
        """Generate barcode image from barcode number"""
        for record in self:
            if record.barcode and BARCODE_AVAILABLE:
                try:
                    # Create Code128 barcode with ImageWriter
                    code = Code128(record.barcode, writer=ImageWriter())
                    
                    # Create a temporary BytesIO file-like object
                    buffer = io.BytesIO()
                    
                    # Write barcode to buffer with options
                    code.write(buffer, options={
                        'module_width': 0.5,
                        'module_height': 15.0,
                        'quiet_zone': 6.5,
                        'font_size': 10,
                        'text_distance': 5.0,
                        'background': 'white',
                        'foreground': 'black',
                    })
                    
                    # Get the image data
                    buffer.seek(0)
                    img_data = buffer.read()
                    
                    if img_data and len(img_data) > 0:
                        # Convert to base64
                        record.barcode_image = base64.b64encode(img_data).decode('utf-8')
                        _logger.info(f'Barcode image generated successfully for barcode: {record.barcode}, size: {len(img_data)} bytes')
                    else:
                        _logger.warning(f'Empty barcode image generated for barcode: {record.barcode}')
                        record.barcode_image = False
                except Exception as e:
                    _logger.error(f'Error generating barcode image for {record.barcode}: {str(e)}', exc_info=True)
                    # Try alternative method using render
                    try:
                        writer = ImageWriter()
                        img = code.render(writer)
                        buffer = io.BytesIO()
                        img.save(buffer, format='PNG')
                        buffer.seek(0)
                        img_data = buffer.getvalue()
                        if img_data:
                            record.barcode_image = base64.b64encode(img_data).decode('utf-8')
                            _logger.info(f'Barcode image generated using render method for barcode: {record.barcode}')
                        else:
                            record.barcode_image = False
                    except Exception as e2:
                        _logger.error(f'Error with alternative barcode generation method: {str(e2)}')
                        record.barcode_image = False
            else:
                if not record.barcode:
                    _logger.debug(f'No barcode for registration {record.id}')
                if not BARCODE_AVAILABLE:
                    _logger.debug('BARCODE library not available')
                record.barcode_image = False

    def _format_phone_number_for_whatsapp(self):
        """Return digits-only phone number for WhatsApp."""
        self.ensure_one()
        phone_candidates = [
            self.phone,
            self.partner_id.mobile if self.partner_id else False,
            self.partner_id.phone if self.partner_id else False,
        ]
        for number in phone_candidates:
            if not number:
                continue
            cleaned = ''.join(filter(str.isdigit, str(number)))
            if cleaned:
                return cleaned
        return False
    
    def _generate_badge_image(self):
        """Generate badge image from PDF badge report"""
        self.ensure_one()
        
        if not PDF_TO_IMAGE_AVAILABLE:
            _logger.warning('pdf2image library not available. Cannot generate badge image.')
            return False
        
        try:
            # Get the badge report XML ID
            report_xmlid = 'event.action_report_event_registration_badge'
            
            # Verify report exists
            report = self.env.ref(report_xmlid, raise_if_not_found=False)
            if not report:
                _logger.warning('Badge report not found')
                return False
            
            # Render PDF using ir.actions.report model
            # _render_qweb_pdf returns (pdf_content, report_type) tuple
            result = self.env['ir.actions.report']._render_qweb_pdf(
                report_xmlid, 
                res_ids=self.ids
            )
            
            if not result:
                _logger.warning('Failed to generate PDF badge')
                return False
            
            # Extract PDF content (first element of tuple)
            pdf_content = result[0] if isinstance(result, tuple) else result
            if not pdf_content:
                _logger.warning('PDF content is empty')
                return False
            
            # Convert PDF to image
            images = convert_from_bytes(pdf_content, dpi=200, first_page=1, last_page=1)
            if not images:
                _logger.warning('Failed to convert PDF to image')
                return False
            
            # Convert PIL Image to base64
            img = images[0]
            
            # Convert to RGB if necessary (some PDFs might be in different mode)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Save to bytes
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG', quality=95)
            img_buffer.seek(0)
            
            # Convert to base64
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
            
            # Generate filename
            event_name = (self.event_id.name or 'Event').replace('/', '_').replace('\\', '_')
            attendee_name = (self.name or 'Attendee').replace('/', '_').replace('\\', '_')
            filename = f'badge_{event_name}_{attendee_name}_{self.id}.png'
            
            return {
                'badge_image': img_base64,
                'badge_image_filename': filename
            }
            
        except Exception as e:
            _logger.error(f'Error generating badge image: {str(e)}', exc_info=True)
            return False
    
    def action_generate_badge_image(self):
        """Action to manually generate badge image"""
        self.ensure_one()
        result = self._generate_badge_image()
        if result:
            self.write(result)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Badge Image',
                    'message': '✅ Badge image generated successfully!',
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Badge Image',
                    'message': '❌ Failed to generate badge image. Please check logs and ensure pdf2image and pillow are installed.',
                    'type': 'danger',
                }
            }
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate badge image"""
        registrations = super(EventRegistration, self).create(vals_list)
        
        # Generate badge images for new registrations
        for registration in registrations:
            if registration.state in ('open', 'done'):
                try:
                    result = registration._generate_badge_image()
                    if result:
                        registration.write(result)
                except Exception as e:
                    _logger.error(f'Error generating badge image for registration {registration.id}: {str(e)}')
        
        return registrations
    
    def write(self, vals):
        """Override write to regenerate badge image when state changes to open or done"""
        result = super(EventRegistration, self).write(vals)
        
        # Regenerate badge image if state changed to open or done
        if 'state' in vals:
            for registration in self:
                if registration.state in ('open', 'done') and not registration.badge_image:
                    try:
                        badge_result = registration._generate_badge_image()
                        if badge_result:
                            registration.write(badge_result)
                    except Exception as e:
                        _logger.error(f'Error generating badge image for registration {registration.id}: {str(e)}')
        
        return result


