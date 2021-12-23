from odoo import api, fields, models


class AccountTax(models.Model):
    _name = 'account.tax'
    _inherit = "account.tax"

    option_lcv = fields.Selection([
        ('iva', 'IVA'),
        ('none', 'NO APLICA'),
    ], string=u"Aplicación LCV", default='none',
        help=u"Opción SIN para aplicar el impuesto en caso de usarse el calculo en libro de compras o ventas")

    credit_debit_account_id = fields.Many2one('account.account', domain=[('deprecated', '=', False)],
                                              string='Notas de credito/Debito', ondelete='restrict',
                                              help="Cuenta que utiliza al registrar una nota de crédito debito")

    # ----UNIVERSAL DISCOUNT----
    control_tax = fields.Boolean(string="Aplicar descuento")