# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import urllib.request
import urllib.error
import json
import subprocess
import io
import base64
import logging

_logger = logging.getLogger(__name__)

try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False
    _logger.warning('qrcode library not available. Install with: pip install qrcode[pil]')


class WhatsAppQRSession(models.Model):
    _name = 'whatsapp.qr.session'
    _description = 'WhatsApp QR Code Session'
    _order = 'create_date desc'

    name = fields.Char(string='Session', default='WhatsApp Session', required=True)
    qr_code_image = fields.Binary(
        string='QR Code Image',
        attachment=True,
        help='Scan this QR code with WhatsApp mobile app'
    )
    qr_code_text = fields.Text(
        string='QR Code Raw Data',
        readonly=True,
        help='Raw QR code content'
    )
    status = fields.Selection([
        ('disconnected', 'Disconnected'),
        ('qr_ready', 'QR Ready - Scan Now'),
        ('connected', 'Connected'),
    ], string='Status', default='disconnected', readonly=True)
    
    server_url = fields.Char(
        string='Server URL',
        compute='_compute_server_url',
        store=False
    )
    
    container_name = fields.Char(
        string='Container Name',
        compute='_compute_container_name',
        store=False
    )
    
    @api.depends_context('company')
    def _compute_server_url(self):
        for record in self:
            record.server_url = self.env['ir.config_parameter'].sudo().get_param(
                'whatsapp_wedding_invitations.server_url',
                'http://localhost:3000'
            )
    
    @api.depends_context('company')
    def _compute_container_name(self):
        for record in self:
            record.container_name = self.env['ir.config_parameter'].sudo().get_param(
                'whatsapp_wedding_invitations.container_name',
                'whatsapp-bridge'
            )
    
    def action_refresh_qr(self):
        """Refresh QR code from WhatsApp server"""
        self.ensure_one()
        self._ensure_whatsapp_bridge_running()
        
        server_url = self.server_url
        qr_endpoint = f'{server_url}/api/qr-code'
        
        try:
            req = urllib.request.Request(qr_endpoint)
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status != 200:
                    raise UserError(f'Cannot fetch QR code. Status code: {response.status}')
                data = json.loads(response.read().decode())
        except urllib.error.URLError as e:
            self.write({
                'qr_code_image': False,
                'qr_code_text': False,
                'status': 'disconnected'
            })
            raise UserError(f'Cannot connect to WhatsApp server at {server_url}. Error: {str(e)}')
        except Exception as e:
            self.write({
                'qr_code_image': False,
                'qr_code_text': False,
                'status': 'disconnected'
            })
            raise UserError(f'Error while fetching QR code: {str(e)}')
        
        if data.get('ready'):
            self.write({
                'qr_code_image': False,
                'qr_code_text': False,
                'status': 'connected'
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'WhatsApp Connection',
                    'message': '✅ WhatsApp is already connected!',
                    'type': 'success',
                }
            }
        
        qr_code = data.get('qrCode')
        qr_code_image = data.get('qrCodeImage')
        if not qr_code:
            self.write({
                'qr_code_image': False,
                'qr_code_text': False,
                'status': 'disconnected'
            })
            raise UserError('QR code not available yet. Please try again in a few seconds.')
        
        # Generate QR image
        try:
            if qr_code_image:
                _logger.info('Using server-provided QR image')
                qr_binary = self._data_url_to_binary(qr_code_image)
            else:
                _logger.info('Generating QR image from string: %s...', qr_code[:50])
                qr_binary = self._generate_qr_image(qr_code)
            
            if not qr_binary:
                raise UserError('Failed to generate QR code image. Please check the server logs.')
            
            _logger.info('QR image generated successfully, size: %d bytes', len(qr_binary))
            
            self.write({
                'qr_code_image': qr_binary,
                'qr_code_text': qr_code,
                'status': 'qr_ready'
            })
        except Exception as e:
            _logger.error('Error generating QR image: %s', str(e), exc_info=True)
            raise UserError(f'Failed to generate QR code image: {str(e)}')
        
        # Return action to reload the form view so the image appears
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'whatsapp.qr.session',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_notification': '📱 QR code refreshed! Scan it with WhatsApp mobile app within 60 seconds.'
            }
        }
    
    def action_check_status(self):
        """Check WhatsApp connection status"""
        self.ensure_one()
        server_url = self.server_url
        status_url = f'{server_url}/api/status'
        
        try:
            req = urllib.request.Request(status_url)
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    if data.get('ready'):
                        self.write({'status': 'connected'})
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': 'WhatsApp Connection',
                                'message': '✅ WhatsApp server is connected and ready!',
                                'type': 'success',
                            }
                        }
                    else:
                        self.write({'status': 'disconnected'})
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': 'WhatsApp Connection',
                                'message': '⚠️ WhatsApp server is running but not connected. Please scan the QR code.',
                                'type': 'warning',
                            }
                        }
                raise UserError(f'❌ Cannot connect to WhatsApp server. Status code: {response.status}')
        except urllib.error.URLError as e:
            self.write({'status': 'disconnected'})
            raise UserError(f'❌ Cannot connect to WhatsApp server at {server_url}. Error: {str(e)}')
        except Exception as e:
            raise UserError(f'❌ Error: {str(e)}')
    
    def _ensure_whatsapp_bridge_running(self):
        """Ensure the Docker container hosting the WhatsApp bridge is running."""
        container_name = self.container_name
        check_cmd = [
            'docker', 'ps',
            '--filter', f'name=^{container_name}$',
            '--format', '{{.Status}}'
        ]
        try:
            result = subprocess.run(
                check_cmd,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except FileNotFoundError:
            raise UserError('Docker command not found. Please install Docker and ensure it is in the PATH.')
        except subprocess.TimeoutExpired:
            raise UserError('Checking Docker container status timed out.')

        if result.returncode != 0:
            raise UserError(f'Failed to check Docker container status: {result.stderr}')

        status = result.stdout.strip()
        if not status or 'Exited' in status:
            # Container is not running, try to start it
            start_cmd = ['docker', 'start', container_name]
            try:
                start_result = subprocess.run(
                    start_cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if start_result.returncode != 0:
                    raise UserError(f'Failed to start Docker container "{container_name}": {start_result.stderr}')
            except subprocess.TimeoutExpired:
                raise UserError(f'Starting Docker container "{container_name}" timed out.')
            except Exception as e:
                raise UserError(f'Error starting Docker container: {str(e)}')

    def _data_url_to_binary(self, data_url):
        """Convert data URL to base64 string for Odoo Binary field."""
        if not data_url:
            return False
        try:
            header, encoded = data_url.split(',', 1)
            # Return the base64 string directly (Odoo Binary field expects base64)
            return encoded
        except (ValueError, Exception):
            return False

    def _generate_qr_image(self, qr_string):
        """Generate QR code image from string using qrcode library."""
        if not QRCODE_AVAILABLE:
            raise UserError(
                'QR code generation library not available. '
                'Please install it with: pip install qrcode[pil]'
            )
        
        if not qr_string:
            return False
        
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_string)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert PIL image to base64 string for Odoo Binary field
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
        except Exception as e:
            raise UserError(f'Error generating QR code image: {str(e)}')

