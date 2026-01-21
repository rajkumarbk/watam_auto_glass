# -*- coding: utf-8 -*-
# models/zk_device.py

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
import socket
import struct
import json
from datetime import datetime

_logger = logging.getLogger(__name__)

class ZKTecoDevice(models.Model):
    _name = 'zk.device'
    _description = 'ZKTeco Fingerprint Device'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Device Name', required=True, tracking=True)
    device_ip = fields.Char('Device IP', required=True, tracking=True)
    device_port = fields.Integer('Device Port', default=4370, required=True)
    adms_ip = fields.Char('ADMS Server IP', help="ADMS server IP for remote devices")
    adms_port = fields.Integer('ADMS Server Port', default=8088, help="ADMS server port")
    use_adms = fields.Boolean('Use ADMS Push', default=False, tracking=True,
                              help="Enable for devices outside local network")
    device_sn = fields.Char('Device Serial Number')
    is_connected = fields.Boolean('Connected', default=False, readonly=True, tracking=True)
    last_sync = fields.Datetime('Last Sync', readonly=True)
    active = fields.Boolean(default=True)
    
    def _create_adms_connection(self):
        """Create connection to ADMS server"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((self.adms_ip, self.adms_port))
            _logger.info(f"Connected to ADMS server: {self.adms_ip}:{self.adms_port}")
            return sock
        except Exception as e:
            _logger.error(f"ADMS connection failed: {str(e)}")
            raise UserError(_("Failed to connect to ADMS server: %s") % str(e))
    
    def _create_direct_connection(self):
        """Create direct connection to device"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((self.device_ip, self.device_port))
            _logger.info(f"Connected directly to device: {self.device_ip}:{self.device_port}")
            return sock
        except Exception as e:
            _logger.error(f"Direct connection failed: {str(e)}")
            raise UserError(_("Failed to connect to device: %s") % str(e))
    
    def _send_adms_request(self, command, data=None):
        """Send request through ADMS to remote device"""
        sock = self._create_adms_connection()
        try:
            # ADMS Protocol: Build request packet
            request = {
                'sn': self.device_sn or self.name,
                'device_ip': self.device_ip,
                'device_port': self.device_port,
                'command': command,
                'data': data or {}
            }
            
            # Convert to JSON and send
            request_json = json.dumps(request).encode('utf-8')
            packet_size = len(request_json)
            
            # Send packet size first (4 bytes)
            sock.sendall(struct.pack('<I', packet_size))
            # Send actual data
            sock.sendall(request_json)
            
            # Receive response size
            response_size = struct.unpack('<I', sock.recv(4))[0]
            # Receive response data
            response_data = b''
            while len(response_data) < response_size:
                chunk = sock.recv(response_size - len(response_data))
                if not chunk:
                    break
                response_data += chunk
            
            response = json.loads(response_data.decode('utf-8'))
            return response
            
        except Exception as e:
            _logger.error(f"ADMS request failed: {str(e)}")
            raise UserError(_("ADMS request failed: %s") % str(e))
        finally:
            sock.close()
    
    def _send_direct_command(self, command_code, data=b''):
        """Send command directly to device (for local network)"""
        sock = self._create_direct_connection()
        try:
            # ZKTeco protocol packet structure
            packet = self._create_packet(command_code, data)
            sock.sendall(packet)
            
            # Receive response
            response = sock.recv(1024)
            return self._parse_response(response)
            
        except Exception as e:
            _logger.error(f"Direct command failed: {str(e)}")
            raise UserError(_("Command failed: %s") % str(e))
        finally:
            sock.close()
    
    def _create_packet(self, command, data=b''):
        """Create ZKTeco protocol packet"""
        # Basic packet structure: [Start(2)] [Size(2)] [Command(2)] [Data] [Checksum(2)]
        start = struct.pack('<H', 0x5050)
        size = struct.pack('<H', len(data) + 8)
        cmd = struct.pack('<H', command)
        
        packet = start + size + cmd + data
        checksum = sum(packet) & 0xFFFF
        packet += struct.pack('<H', checksum)
        
        return packet
    
    def _parse_response(self, response):
        """Parse ZKTeco protocol response"""
        if len(response) < 8:
            return {'success': False, 'error': 'Invalid response'}
        
        start, size, command = struct.unpack('<HHH', response[:6])
        data = response[6:-2]
        checksum = struct.unpack('<H', response[-2:])[0]
        
        return {
            'success': True,
            'command': command,
            'data': data
        }
    
    def test_connection(self):
        """Test connection to device"""
        self.ensure_one()
        try:
            if self.use_adms:
                response = self._send_adms_request('test_connection')
                if response.get('success'):
                    self.write({'is_connected': True})
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'message': _('Successfully connected via ADMS!'),
                            'type': 'success',
                            'sticky': False,
                        }
                    }
            else:
                # Direct connection test (Command 1000 - Connect)
                response = self._send_direct_command(1000)
                if response['success']:
                    self.write({'is_connected': True})
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'message': _('Successfully connected directly!'),
                            'type': 'success',
                            'sticky': False,
                        }
                    }
        except Exception as e:
            self.write({'is_connected': False})
            raise UserError(_("Connection test failed: %s") % str(e))
    
    def sync_attendance_data(self):
        """Sync attendance data from device"""
        self.ensure_one()
        try:
            if self.use_adms:
                response = self._send_adms_request('get_attendance', {
                    'start_time': self.last_sync.isoformat() if self.last_sync else None
                })
                attendance_records = response.get('data', [])
            else:
                # Direct connection (Command 4 - Get attendance records)
                response = self._send_direct_command(4)
                attendance_records = self._parse_attendance_data(response['data'])
            
            # Process attendance records
            self._process_attendance_records(attendance_records)
            
            self.write({
                'last_sync': fields.Datetime.now(),
                'is_connected': True
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Synced %d attendance records') % len(attendance_records),
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.error(f"Sync failed: {str(e)}")
            raise UserError(_("Sync failed: %s") % str(e))
    
    def _parse_attendance_data(self, data):
        """Parse attendance data from device response"""
        records = []
        # ZKTeco attendance record format: user_id(2), timestamp(4), status(1)
        record_size = 7
        
        for i in range(0, len(data), record_size):
            if i + record_size > len(data):
                break
            
            user_id, timestamp, status = struct.unpack('<HIB', data[i:i+record_size])
            records.append({
                'user_id': user_id,
                'timestamp': datetime.fromtimestamp(timestamp),
                'status': status  # 0=Check In, 1=Check Out
            })
        
        return records
    
    def _process_attendance_records(self, records):
        """Process and create attendance records in Odoo"""
        Attendance = self.env['hr.attendance']
        Employee = self.env['hr.employee']
        
        for record in records:
            # Find employee by device user ID
            employee = Employee.search([
                ('zk_user_id', '=', record['user_id'])
            ], limit=1)
            
            if not employee:
                _logger.warning(f"Employee not found for user_id: {record['user_id']}")
                continue
            
            # Check if record already exists
            existing = Attendance.search([
                ('employee_id', '=', employee.id),
                ('check_in', '=', record['timestamp'])
            ], limit=1)
            
            if existing:
                continue
            
            # Create attendance record
            if record['status'] == 0:  # Check In
                Attendance.create({
                    'employee_id': employee.id,
                    'check_in': record['timestamp'],
                })
            else:  # Check Out
                # Find last open attendance
                last_attendance = Attendance.search([
                    ('employee_id', '=', employee.id),
                    ('check_out', '=', False)
                ], order='check_in desc', limit=1)
                
                if last_attendance:
                    last_attendance.write({'check_out': record['timestamp']})


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    
    zk_user_id = fields.Integer('ZK Device User ID', 
                                help="User ID in ZKTeco fingerprint device")
    zk_device_ids = fields.Many2many('zk.device', string='Assigned Devices')