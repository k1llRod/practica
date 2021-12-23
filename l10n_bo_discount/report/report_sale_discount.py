# -*- coding: utf-8 -*-
import datetime
import time

import dateutil.parser

from odoo import api, models, _
from odoo.exceptions import UserError


class ReportSaleDiscount(models.AbstractModel):
    _name = 'report.l10n_bo_discount.report_sale_discount_template'
    _description = 'Reporte de Ventas con Descuento'

    @api.model
    def _get_report_values(self, docids, data=None):
        values = data.get('values', False)
        date_init = dateutil.parser.parse(data.get('date_init', False)).date()
        date_end = dateutil.parser.parse(data.get('date_end', False)).date()
        today = datetime.date.today()
        company = self.env.user.company_id
        if not values:
            raise UserError(_("No se encontraron registros para imprimir el reporte."))
        return {
            'data': data,
            'docs': values,
            'date_init': date_init,
            'date_end': date_end,
            'today': today,
            'company': company,
        }