# -*- coding: utf-8 -*-
# controllers.py

from odoo import http, fields
from odoo.http import request
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class ZkPushController(http.Controller):

    @http.route(['/iclock/cdata', '/iclock/fdata'], type='http', auth="none", csrf=False, methods=['POST'])
    def cdata(self, **kw):
        try:
            data = request.httprequest.data.decode('utf-8')
            sn = kw.get('SN', '')  # Device serial
            device = request.env['zk.device'].sudo().search([('device_sn', '=', sn)], limit=1)
            if not device:
                _logger.warning(f"Unknown device SN: {sn}")
                return 'OK'
            
            lines = data.splitlines()
            for line in lines:
                if 'ATTLOG' in line:
                    parts = line.split('\t')
                    if len(parts) < 3:
                        continue
                    uid_str = parts[0]  # User ID
                    timestamp_str = parts[1]  # YYYY-MM-DD HH:MM:SS
                    status_str = parts[2]  # 0=in, 1=out, etc.
                    # Optional: verify (parts[3]), workcode (parts[4]), etc.
                    try:
                        user_id = int(uid_str)
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        status = int(status_str)
                    except ValueError:
                        continue
                    
                    records = [{'user_id': user_id, 'timestamp': timestamp, 'status': status}]
                    device._process_attendance_records(records)
            
            device.write({'last_sync': fields.Datetime.now()})
            return 'OK'
        except Exception as e:
            _logger.error(f"ADMS push error: {str(e)}")
            return 'OK'  # Always return OK to device

    @http.route('/iclock/getrequest', type='http', auth="none", csrf=False)
    def getrequest(self, **kw):
        sn = kw.get('SN', '')
        # Can return commands like "GET OPTION" or employee sync, but for basic, return empty
        return 'OK'

    @http.route('/iclock/devicecmd', type='http', auth="none", csrf=False, methods=['POST'])
    def devicecmd(self, **kw):
        # Handle command responses if you send any
        return 'OK'