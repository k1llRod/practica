# -*- coding: utf-8 -*-

from odoo import models, fields, api
from .operations.codigo_control_gen import get_codigo_control


class ValidCodeControl(models.Model):
    _name = 'valid_code_control'
    _description = 'Validación de códigos de control para SIN'

    n_autorizacion = fields.Char(string="Nro. Autorización", size=15)
    n_factura = fields.Integer(string="Nro. Factura")
    nit_ci = fields.Char(string=u"NIT/CI", size=12)
    fecha = fields.Date(string=u"Fecha")
    monto = fields.Float(string=u"Monto", digits=(12, 2))
    llave = fields.Char(string=u"Llave", size=200)
    codigo_control = fields.Char(string=u"Código Control", size=100)

    @api.onchange('llave')
    def onchange_llave(self):
        if (self.n_autorizacion
                and self.n_factura
                and self.nit_ci
                and self.fecha
                and self.monto
                and self.llave):
            self.codigo_control = get_codigo_control(self.n_autorizacion,
                                                     self.n_factura,
                                                     self.nit_ci, self.fecha,
                                                     self.monto, self.llave)

    @api.onchange('monto')
    def onchange_monto(self):
        if (self.n_autorizacion
                and self.n_factura
                and self.nit_ci
                and self.fecha
                and self.monto
                and self.llave):
            self.codigo_control = get_codigo_control(self.n_autorizacion,
                                                     self.n_factura,
                                                     self.nit_ci, self.fecha,
                                                     self.monto, self.llave)

    # def get_cc(self):
    #     self.codigo_control = get_codigo_control(self.n_autorizacion,
    #                                              self.n_factura,
    #                                              self.nit_ci, self.fecha,
    #                                              self.monto, self.llave)
