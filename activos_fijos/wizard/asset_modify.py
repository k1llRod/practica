# -*- coding: utf-8 -*-
import calendar
from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from datetime import date, timedelta
from odoo.tools import float_compare, float_is_zero, float_round
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from datetime import datetime
from math import copysign

from odoo.tools.populate import compute

class AssetModify(models.TransientModel):
    _inherit = 'asset.modify'

    account_inflation_tenure_id = fields.Many2one('account.account', 'Ajuste por inflación y tenencia de bienes')
    minium_limit = fields.Float(string='Limite mínimo %',readonly=True)
    minium_value = fields.Float(string='Valor mínimo', readonly=True)

    def modify(self):
        """ Modifies the duration of asset for calculating depreciation
        and maintains the history of old values, in the chatter.
        """

        old_values = {
            'method_number': self.asset_id.method_number,
            'method_period': self.asset_id.method_period,
            'value_residual': self.asset_id.value_residual,
            'salvage_value': self.asset_id.salvage_value,
        }

        asset_vals = {
            'method_number': self.method_number,
            'method_period': self.method_period,
            'value_residual': self.value_residual,
            'salvage_value': self.salvage_value,
        }
        if self.need_date:
            asset_vals.update({
                'prorata_date': self.date,
            })
        if self.env.context.get('resume_after_pause'):
            asset_vals.update({'state': 'open'})
            self.asset_id.message_post(body=_("Asset unpaused"))
        else:
            self = self.with_context(ignore_prorata=True)

        current_asset_book = self.asset_id.value_residual + self.asset_id.salvage_value
        after_asset_book = self.value_residual + self.salvage_value
        increase = after_asset_book - current_asset_book

        if not increase >= self.minium_value:
            raise UserError('No cumple con el valor mínimo para modificar el activo fijo')

        new_residual = min(current_asset_book - min(self.salvage_value, self.asset_id.salvage_value), self.value_residual)
        new_salvage = min(current_asset_book - new_residual, self.salvage_value)
        residual_increase = max(0, self.value_residual - new_residual)
        salvage_increase = max(0, self.salvage_value - new_salvage)

        # Check for residual/salvage increase while rounding with the company currency precision to prevent float precision issues.
        if  self.currency_id.round(residual_increase + salvage_increase) > 0:
            move = self.env['account.move'].create({
                'journal_id': self.asset_id.journal_id.id,
                'date': fields.Date.today(),
                'line_ids': [
                    (0, 0, {
                        'account_id': self.account_asset_id.id,
                        'debit': residual_increase + salvage_increase,
                        'credit': 0,
                        'name': _('Value increase for: %(asset)s', asset=self.asset_id.name),
                    }),
                    (0, 0, {
                        'account_id': self.account_asset_counterpart_id.id,
                        'debit': 0,
                        'credit': residual_increase + salvage_increase,
                        'name': _('Value increase for: %(asset)s', asset=self.asset_id.name),
                    }),
                ],
            })
            move._post()
            asset_increase = self.env['account.asset'].create({
                'name': self.asset_id.name + ': ' + self.name,
                'currency_id': self.asset_id.currency_id.id,
                'company_id': self.asset_id.company_id.id,
                'asset_type': self.asset_id.asset_type,
                'method': self.asset_id.method,
                'method_number': self.method_number,
                'method_period': self.method_period,
                'acquisition_date': self.date,
                'value_residual': residual_increase,
                'salvage_value': salvage_increase,
                'original_value': residual_increase + salvage_increase,
                'account_asset_id': self.account_asset_id.id,
                'account_depreciation_id': self.account_depreciation_id.id,
                'account_depreciation_expense_id': self.account_depreciation_expense_id.id,
                'journal_id': self.asset_id.journal_id.id,
                'parent_id': self.asset_id.id,
                'account_inflation_tenure_id': self.account_inflation_tenure_id.id,
                'original_move_line_ids': [(6, 0, move.line_ids.filtered(lambda r: r.account_id == self.account_asset_id).ids)],
            })
            asset_increase.validate()

            subject = _('A gross increase has been created') + ': <a href=# data-oe-model=account.asset data-oe-id=%d>%s</a>' % (asset_increase.id, asset_increase.name)
            self.asset_id.message_post(body=subject)
        if increase < 0:
            if self.env['account.move'].search([('asset_id', '=', self.asset_id.id), ('state', '=', 'draft'), ('date', '<=', self.date)]):
                raise UserError('There are unposted depreciations prior to the selected operation date, please deal with them first.')
            move = self.env['account.move'].create(self.env['account.move']._prepare_move_for_asset_depreciation({
                'amount': -increase,
                'asset_id': self.asset_id,
                'move_ref': _('Value decrease for: %(asset)s', asset=self.asset_id.name),
                'date': self.date,
                'asset_remaining_value': 0,
                'asset_depreciated_value': 0,
                'asset_value_change': True,
            }))._post()

        asset_vals.update({
            'value_residual': new_residual,
            'salvage_value': new_salvage,
        })
        #self.asset_id.write(asset_vals)
        #self.asset_id.compute_depreciation_board()
        # self.asset_id.children_ids.write({
        #     'method_number': asset_vals['method_number'],
        #     'method_period': asset_vals['method_period'],
        # })
        for child in self.asset_id.children_ids:
            child.compute_depreciation_board()
        tracked_fields = self.env['account.asset'].fields_get(old_values.keys())
        changes, tracking_value_ids = self.asset_id._message_track(tracked_fields, old_values)
        if changes:
            self.asset_id.message_post(body=_('Depreciation board modified') + '<br>' + self.name, tracking_value_ids=tracking_value_ids)
        return {'type': 'ir.actions.act_window_close'}

