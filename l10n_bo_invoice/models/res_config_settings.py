from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_discount = fields.Boolean(string="Activar Descuento Universal",
                                     related='company_id.enable_discount',
                                     readonly=False)
    sales_discount_product = fields.Many2one('product.product', string="Items Descuento",
                                             related='company_id.sales_discount_product',
                                             readonly=False)
    purchase_discount_product = fields.Many2one('product.product',
                                                string="Items Descuento Compras",
                                                related='company_id.purchase_discount_product',
                                                readonly=False)
    enable_invoice_import = fields.Boolean(
        string="Factura de importación",
        related='company_id.enable_invoice_import',
        readonly=False
    )

    lot_commission = fields.Boolean(string="Comision por Lote")

    enable_accrued_expense = fields.Boolean('Devengado', help='Habilitar facturas de proveedor con gastos devengados')

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('l10n_bo_invoice.enable_accrued_expense', self.enable_accrued_expense)
        self.env['ir.config_parameter'].sudo().set_param('l10n_bo_invoice.lot_commission', self.lot_commission)

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        enable_accrued_expense = self.env['ir.config_parameter'].get_param('l10n_bo_invoice.enable_accrued_expense')
        lot_commission = self.env['ir.config_parameter'].get_param('l10n_bo_invoice.lot_commission')
        res.update({'enable_accrued_expense': enable_accrued_expense,
                    'lot_commission':lot_commission})
        return res