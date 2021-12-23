from odoo import api, fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _default_visible_commission(self):
        return self.env['ir.config_parameter'].sudo().get_param('l10n_bo_invoice.lot_commission')

    visible_commission = fields.Boolean('Visible comission',
                                        compute='_compute_visible_commission',
                                        default=lambda self: self._default_visible_commission())

    commission_grouping_account_id = fields.Many2one('account.account', string="Cuenta de Agrupacion Comisiones",
                                                     domain=lambda self: "[('deprecated', '=', False), ('company_id', '=', company_id), \
                                                                          ('user_type_id.type', 'not in', ('receivable', 'payable')), \
                                                                          '|', ('user_type_id', '=', %s), ('id', '=', default_account_id)]" % self.env.ref(
                                                                          'account.data_account_type_current_assets').id)

    applicable_tax = fields.Many2one(
        comodel_name='account.tax',
        string='Impuesto aplicable',
    )
    bank_commission_rate = fields.Float(
        string='Tasa de comisión bancaria',
        default=0.0,
    )
    # accounting_account = fields.Many2one(
    #     comodel_name='account.account',
    #     string='Cuenta contable'
    # )

    def _compute_visible_commission(self):
        visibility = self.env['ir.config_parameter'].sudo().get_param('l10n_bo_invoice.lot_commission')
        for line in self:
            line.visible_commission = visibility

