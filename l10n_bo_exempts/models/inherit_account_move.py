# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class InheritAccountMove(models.Model):
    _inherit = 'account.move'

    sum_exento = fields.Float(
        string='Sumatoria exentos',
        compute='_compute_sum_exento',
        readonly=False,
        store=True,
    )
    not_calculated = fields.Boolean(
        string='Exentos no calculados',
        default=False,
    )
    my_process_exe = fields.Boolean('Calcular Exentos')

    exento_activated = fields.Boolean(
        string='Exento activado',
        default=False,
    )

    @api.onchange('my_process_exe')
    def onchange_my_process_exe(self):
        lines = self.env['account.move.line']
        for rec in self:
            vals = {
                'sequence': 10000,
                'name': 'EXENTOS',
                'move_id': rec.id,
                'price_unit': self.sum_exento,
                'quantity': 1,
                'company_id': rec.company_id.id,
                'row_exento': True,
            }
            row_exento = False
            account_id = 0
            for lns in self.invoice_line_ids:
                account_id = lns._get_computed_account()
                if lns.row_exento:
                    row_exento=True
                    lines = lns

            if not row_exento and account_id:
                new_line = lines.new(vals)
                new_line.account_id = account_id
                new_line.recompute_tax_line = True
                new_line._onchange_price_subtotal()
                rec._recompute_dynamic_lines()
                lines = new_line

                # EXENTO ACTIVADO
                rec.exento_activated = True
            else:
                lines.update({
                    'price_unit': self.sum_exento,
                    'sequence': 10000
                })
                lines.recompute_tax_line = True
                lines._onchange_price_subtotal()
                rec._recompute_dynamic_lines()

            if rec.sum_exento == 0:
                rec.invoice_line_ids = rec.invoice_line_ids.filtered(lambda x: x.row_exento == False)
                rec.line_ids = rec.line_ids.filtered(lambda x: x.row_exento == False)
                rec.exento_activated = False

    @api.depends('invoice_line_ids.amount_exe')
    def _compute_sum_exento(self):
        amount_exe = 0
        for move in self:
            if move.state == 'draft' and move.move_type == 'in_invoice':

                if move.invoice_line_ids:
                    for line_inv in move.invoice_line_ids:
                        amount_exe += line_inv.amount_exe

                    if move.sum_exento != amount_exe:
                        move.not_calculated = True
                    else:
                        move.not_calculated = False

                    move.sum_exento = amount_exe


                    #test
                    if move.sum_exento == 0 and move.not_calculated and not move.exento_activated:
                        move.not_calculated = False

                    # Linea EXENTO borrada
                    find_row_exento = move.invoice_line_ids.filtered(lambda x: x.row_exento == True)
                    if not find_row_exento and move.exento_activated:
                        move.not_calculated = True
                        move.exento_activated = False

                    # if move.sum_exento == 0:
                    #     move.not_calculated = False

    @api.constrains('not_calculated')
    def check_not_calculated(self):
        for r in self:
            if r.not_calculated and r.move_type == 'in_invoice':
                raise UserError(_('Debe calcular los exentos'))


class InheritAccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    row_exento = fields.Boolean(
        string='Fila exento',
        default=False,
        store=True,
    )
    amount_exe_aux = fields.Boolean(
        string='Auxiliar exe',
        default=False,
        store=False,
    )

    @api.onchange('amount_exe')
    def _compute_amount_exe(self):
        if not self.row_exento and self.move_id.move_type == 'in_invoice':
            amount_exe = (self.amount_exe / self.quantity)
            price = self.price_unit
            if (price - amount_exe) >= 0:
                self.price_unit = price - amount_exe
                self.account_id = self._get_computed_account()
                self.recompute_tax_line = True
                self._onchange_price_subtotal()
                self.amount_exe_aux = True
            else:
                raise UserError(_("El valor de EXENTO no puede ser mayor o igual al precio"))

    @api.onchange('quantity', 'price_unit')
    def _onchange_quantity_price_unit(self):
        if self.move_id.move_type == 'in_invoice':
            for mv in self:
                if not mv.amount_exe_aux:
                    mv.amount_exe = 0
                    mv.amount_exe_aux = False