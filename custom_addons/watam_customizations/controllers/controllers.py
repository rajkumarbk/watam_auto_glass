# -*- coding: utf-8 -*-
# from odoo import http


# class WatamCustomizations(http.Controller):
#     @http.route('/watam_customizations/watam_customizations', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/watam_customizations/watam_customizations/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('watam_customizations.listing', {
#             'root': '/watam_customizations/watam_customizations',
#             'objects': http.request.env['watam_customizations.watam_customizations'].search([]),
#         })

#     @http.route('/watam_customizations/watam_customizations/objects/<model("watam_customizations.watam_customizations"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('watam_customizations.object', {
#             'object': obj
#         })

