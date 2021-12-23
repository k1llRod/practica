from odoo import fields, models, api


class ResUser(models.Model):
    _name = 'res.users'
    _inherit = ['res.users', 'mail.thread', 'mail.activity.mixin']

    warehouse_id = fields.Many2one('stock.warehouse', 'Almacén')
