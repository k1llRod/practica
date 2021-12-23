from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    razon_social = fields.Char(string='Razón Social', size=100, required=True,
                               default='S/N')
    nit_ci = fields.Char(string='NIT/CI', size=12, required=True, index=True,
                         default='0')

    account_discount_id = fields.Many2one(
        'account.account',
        string="Cuenta Registro descuento",
        help="Cuenta contable donde se registrara el descuento de las facturas"
    )
    amount_valid = fields.Monetary(string='Importe Facturas', default=0,
                                   help='Importe maximo permitido para factura con NIT o CI = 0 y Razon Social a S/N')

    # ----UNIVERSAL DISCOUNT----
    enable_discount = fields.Boolean(string="Activar Descuento Universal")
    sales_discount_product = fields.Many2one('product.product',
                                             string="Items Descuento")
    purchase_discount_product = fields.Many2one('product.product',
                                                string="Items Descuento Compras")

    enable_invoice_import = fields.Boolean(string="Factura de importación")