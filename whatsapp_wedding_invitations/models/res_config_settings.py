# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import urllib.request
import urllib.error
import json
import base64
import subprocess
import time
from io import BytesIO


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    whatsapp_server_url = fields.Char(
        string='WhatsApp Server URL',
        config_parameter='whatsapp_wedding_invitations.server_url',
        default='http://localhost:3000',
        help='URL of the WhatsApp server (e.g., http://localhost:3000)'
    )
    
    whatsapp_delay_between_messages = fields.Integer(
        string='Delay Between Messages (ms)',
        config_parameter='whatsapp_wedding_invitations.delay_between_messages',
        default=2000,
        help='Delay in milliseconds between sending messages to avoid rate limiting'
    )
    
    whatsapp_qr_code_image = fields.Binary(
        string='WhatsApp QR Code Image',
        readonly=True,
        help='Preview of the WhatsApp QR code returned by the server'
    )
    
    whatsapp_qr_code_text = fields.Text(
        string='QR Code Raw Data',
        readonly=True,
        help='Raw QR code content as returned by the WhatsApp server'
    )

    whatsapp_bridge_container_name = fields.Char(
        string='Docker Container Name',
        config_parameter='whatsapp_wedding_invitations.docker_container',
        default='whatsapp-bridge',
        help='Name of the Docker container that runs the WhatsApp bridge'
    )
    
    def action_test_whatsapp_connection(self):
        """Test connection to WhatsApp server"""
        self.ensure_one()
        server_url = self.whatsapp_server_url or 'http://localhost:3000'
        status_url = f'{server_url}/api/status'
        
        try:
            req = urllib.request.Request(status_url)
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    if data.get('ready'):
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'title': 'WhatsApp Connection',
                                'message': '✅ WhatsApp server is connected and ready!',
                                'type': 'success',
                                'sticky': False,
                            }
                        }
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': 'WhatsApp Connection',
                            'message': '⚠️ WhatsApp server is running but not connected. Please scan the QR code.',
                            'type': 'warning',
                            'sticky': False,
                        }
                    }
                raise UserError(f'❌ Cannot connect to WhatsApp server. Status code: {response.status}')
        except urllib.error.URLError as e:
            raise UserError(f'❌ Cannot connect to WhatsApp server at {server_url}. Please make sure the server is running. Error: {str(e)}')
        except Exception as e:
            raise UserError(f'❌ Error: {str(e)}')

    def action_fetch_whatsapp_qr_code(self):
        """Fetch QR code from WhatsApp server and display it"""
        self.ensure_one()
        self._ensure_whatsapp_bridge_running()
        server_url = self.whatsapp_server_url or 'http://localhost:3000'
        qr_endpoint = f'{server_url}/api/qr-code'
        
        try:
            req = urllib.request.Request(qr_endpoint)
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status != 200:
                    raise UserError(f'Cannot fetch QR code. Status code: {response.status}')
                data = json.loads(response.read().decode())
        except urllib.error.URLError as e:
            self.whatsapp_qr_code_image = False
            self.whatsapp_qr_code_text = False
            raise UserError(f'Cannot connect to WhatsApp server at {server_url}. Error: {str(e)}')
        except Exception as e:
            self.whatsapp_qr_code_image = False
            self.whatsapp_qr_code_text = False
            raise UserError(f'Error while fetching QR code: {str(e)}')
        
        if data.get('ready'):
            self.whatsapp_qr_code_image = False
            self.whatsapp_qr_code_text = False
            raise UserError('WhatsApp server is already connected. Log out first if you want to regenerate the QR code.')
        
        qr_code = data.get('qrCode')
        qr_code_image = data.get('qrCodeImage')
        if not qr_code:
            self.whatsapp_qr_code_image = False
            self.whatsapp_qr_code_text = False
            raise UserError('QR code not available yet. Please try again in a few seconds.')
        
        if qr_code_image:
            self.whatsapp_qr_code_image = self._data_url_to_binary(qr_code_image)
        else:
            self.whatsapp_qr_code_image = self._generate_qr_image(qr_code)
        self.whatsapp_qr_code_text = qr_code
        
        # Return action to reload the form so the image updates
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def _ensure_whatsapp_bridge_running(self):
        """Ensure the Docker container hosting the WhatsApp bridge is running."""
        container_name = self.whatsapp_bridge_container_name or 'whatsapp-bridge'
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
            raise UserError(f'Failed to check Docker container status: {result.stderr.strip()}')

        status = result.stdout.strip()
        if status.startswith('Up'):
            return

        start_cmd = ['docker', 'start', container_name]
        try:
            start_result = subprocess.run(
                start_cmd,
                capture_output=True,
                text=True,
                timeout=20,
            )
        except subprocess.TimeoutExpired:
            raise UserError(f'Timed out while starting Docker container "{container_name}".')

        if start_result.returncode != 0:
            raise UserError(f'Could not start Docker container "{container_name}": {start_result.stderr.strip()}')

        time.sleep(2)  # Give the server a brief moment to boot

    def _data_url_to_binary(self, data_url):
        """Convert data URL to base64 bytes usable by Binary fields."""
        if not data_url:
            return False
        try:
            _, encoded = data_url.split(',', 1)
        except ValueError:
            return False
        return encoded.encode('utf-8')

    def _generate_qr_image(self, qr_string):
        """Generate QR code PNG data (base64-encoded) from the provided string."""
        if not qr_string:
            return False
        try:
            import qrcode
        except ImportError:
            raise UserError(
                'Python package "qrcode" is required to generate the QR image. '
                'Install it with: pip install qrcode[pil]'
            )

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(qr_string)
        qr.make(fit=True)

        img = qr.make_image(fill_color='black', back_color='white')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue())

