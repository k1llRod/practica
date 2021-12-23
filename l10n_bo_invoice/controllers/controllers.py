# -*- coding: utf-8 -*-
# from odoo import http


# class 10nLocalizatonBo(http.Controller):
#     @http.route('/10n_localizaton_bo/10n_localizaton_bo/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/10n_localizaton_bo/10n_localizaton_bo/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('10n_localizaton_bo.listing', {
#             'root': '/10n_localizaton_bo/10n_localizaton_bo',
#             'objects': http.request.env['10n_localizaton_bo.10n_localizaton_bo'].search([]),
#         })

#     @http.route('/10n_localizaton_bo/10n_localizaton_bo/objects/<model("10n_localizaton_bo.10n_localizaton_bo"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('10n_localizaton_bo.object', {
#             'object': obj
#         })
