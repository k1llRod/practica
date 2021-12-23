from odoo import models, fields, api
from datetime import date, datetime


class WizardSaleDiscount(models.TransientModel):
    _name = "wizard.sale.discount"
    _description = "wizard de descuentos en las ventas"

    date_init = fields.Date('Fecha Inicio', required=True)
    date_end = fields.Date('Fecha Inicio ', required=True)
    warehouse_ids = fields.Many2many('stock.warehouse', string='Sucursales')

    def action_get_report(self):
        warehouses = self.mapped('warehouse_ids.id')
        product_discount = self.env.user.company_id.purchase_discount_product
        lines = self.env['account.move.line'].search([
            ('move_id.invoice_date', '>=', self.date_init),
            ('move_id.invoice_date', '<=', self.date_end),
            ('move_id.state', '=', 'posted'),
            ('move_id.move_type', '=', 'out_invoice'),
            ('move_id.state_sin', '=', 'V'),
            ('product_id', '!=', product_discount.id),
            ('exclude_from_invoice_tab', '=', False),
            ('display_type', '=', False),
            ('move_id.warehouse_id', 'in', warehouses)
        ], order='id asc')
        data = {}
        for line in lines:
            category = line.product_id.categ_id
            self.recursive_func(data, line, category)
        info = {
            'values': data,
            'date_init': self.date_init,
            'date_end': self.date_end
        }
        return self.env.ref('l10n_bo_discount.report_sale_discount_action').report_action(self, data=info)

    def recursive_func(self, data, line, category):
        if category.parent_id:
            self.recursive_func(data, line, category.parent_id)
        else:
            cost = line.quantity * line.product_id.standard_price
            if not category.id in data:
                data.update({
                    category.id: {
                        'name': category.name,
                        'quantity': line.quantity,
                        'total_sale': round(line.price_total, 2),
                        'discount': round(line.total_discount, 2),
                        'standard_price': round(cost, 2)
                    }
                })
            else:
                data[category.id]['quantity'] += line.quantity
                data[category.id]['total_sale'] += round(line.price_total,2)
                data[category.id]['discount'] += round(line.total_discount, 2)
                data[category.id]['standard_price'] += round(cost, 2)