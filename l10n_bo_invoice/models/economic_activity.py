from odoo import api, fields, models


class EconomicActivity(models.Model):
    _name = 'economic.activity'
    _description = 'Actividades económicas'
    _order = "name"

    name = fields.Char(string="Código/Nombre",
                       help="Nombre y Actividad Economica del contribuyente")
