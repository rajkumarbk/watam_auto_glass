# -*- coding: utf-8 -*-
# from odoo import http


# class ZktecoDevice(http.Controller):
#     @http.route('/zkteco_device/zkteco_device', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/zkteco_device/zkteco_device/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('zkteco_device.listing', {
#             'root': '/zkteco_device/zkteco_device',
#             'objects': http.request.env['zkteco_device.zkteco_device'].search([]),
#         })

#     @http.route('/zkteco_device/zkteco_device/objects/<model("zkteco_device.zkteco_device"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('zkteco_device.object', {
#             'object': obj
#         })

