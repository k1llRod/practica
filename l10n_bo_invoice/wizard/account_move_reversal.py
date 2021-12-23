# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import datetime


class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"

    invoice_date_origin = fields.Date(string='Fecha Asiento Original', default=fields.Date.context_today, required=True,
                                      readonly=True)
    nota_credito_debito = fields.Boolean(string=u'Nota de Crédito/Débito')

    @api.model
    def default_get(self, fields):
        res = super(AccountMoveReversal, self).default_get(fields)
        res_ids = self._context.get('active_ids')
        inv = self.env['account.move'].browse(res_ids[0])
        mes_factura = inv.date.month
        mes_rectificado = datetime.date.today().month
        res_b = False
        if mes_factura != mes_rectificado:
            res_b = True
        res.update({
            'invoice_date_origin': inv.date,
            'nota_credito_debito': res_b,
        })
        return res

    @api.onchange('date')
    def _onchange_invoice_date(self):
        mes_factura = self.date.month
        mes_rectificado = self.date.month
        if mes_factura != mes_rectificado:
            self.nota_credito_debito = True
        else:
            self.nota_credito_debito = False

    def reverse_moves(self):
        res = super(AccountMoveReversal, self).reverse_moves()
        moves = self.env['account.move'].browse(self.env.context['active_ids']) if self.env.context.get(
            'active_model') == 'account.move' else self.move_id
        for wiz in self:
            if wiz.nota_credito_debito:
                moves.note_credit_debit = True
                mv_refund = self.env['account.move'].browse(res['res_id'])
                mv_refund.note_credit_debit = True
                mv_refund.warehouse_id = moves.warehouse_id
                mv_refund.dosificacion = moves.warehouse_id.dosificacion_dc
            moves.state_sin = 'A'
        return res
