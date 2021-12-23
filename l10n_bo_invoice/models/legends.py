

from odoo import api, fields, models


class LegendsControl(models.Model):
    _name = 'legend.control'
    _description = 'Leyendas para el control SIN'
    _order = 'name'

    type=fields.Selection([
        ('genericas','Genéricas'),
        ('prestacion_servicio', 'Prestación de Servicios'),
        ('venta_producto', 'Venta de Productos'),
        ('salud', 'Salud'),
        ('servicio_banca', 'Servicios Bancarios y Financieros'),
        ('medios', 'Medios de Comunicación')
    ],required=True, default="genericas",
        help="Seleccionar un tipo de Leyenda para ser categorizado")

    name=fields.Char(string="Descripción")