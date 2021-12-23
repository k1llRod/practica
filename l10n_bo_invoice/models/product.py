from odoo import api, fields, models


class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = 'product.template'

    ali_esp = fields.Float('Alicuota Especifica')
    ali_por = fields.Float('Alicuota Porcentual (0-100%)')
    ali_uom = fields.Many2one('uom.uom', string='Unidad Cobro Alicuota')
    ali_qty = fields.Float(string='Cantidad Cobro')

    # ----UNIVERSAL DISCOUNT----
    product_discount = fields.Boolean('Items de Descuento')