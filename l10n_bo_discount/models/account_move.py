from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class AccountMove(models.Model):
    _inherit = 'account.move'

    global_discount_type = fields.Selection(
        [('percent', 'Porcentaje'), ('amount', 'Monto')],
        string='Tipo de Descuento',
        readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        default='percent')
    global_discount_rate = fields.Float('Descuento General',
                                        readonly=True,
                                        states={'draft': [('readonly', False)],
                                                'sent': [('readonly', False)]})
    cal_discount = fields.Boolean("Calcular Descuento")

    @api.onchange('global_discount_rate', 'global_discount_type')
    def calculate_discount(self):
        for line in self.invoice_line_ids:
            line.update({
                'disc': self.global_discount_rate
            })
            line.onchange_line()
        self.calculate_discount_line()

    @api.onchange("cal_discount")
    def calculate_discount_line(self):
        new_lines = self.env['account.move.line']
        ban_desc = True
        for rec in self:
            total_discount = 0
            line_discount = rec.invoice_line_ids.filtered(lambda x: x.product_id.product_discount is True)
            lines = rec.invoice_line_ids.filtered(lambda x: x.product_id.product_discount is False)
            for l in lines:
                total_discount += l.total_discount
            if line_discount:
                line_discount.price_unit = total_discount * -1
                line_discount._onchange_price_subtotal()
            rec.amount_discount = total_discount
            if rec.amount_discount > 0:
                currency = rec.currency_id
                for line in rec.invoice_line_ids:
                    if line.product_id.product_discount:
                        ban_desc = False
                        new_lines = line
                        break
                if ban_desc and rec.amount_discount > 0:
                    if rec.move_type == 'in_invoice':
                        product = rec.company_id.purchase_discount_product
                    elif rec.move_type == 'out_invoice':
                        product = rec.company_id.sales_discount_product
                    amount = rec.amount_discount
                    vals = {
                        'sequence': 10000,
                        # 'name': '%s: %s' % ('Descuento sobre las ventas'),
                        'name': 'Descuento sobre las ventas',
                        'move_id': rec.id,
                        'currency_id': currency and currency.id or False,
                        'date_maturity': rec.invoice_date_due,
                        'product_uom_id': product.uom_id.id,
                        'product_id': product.id,
                        'price_unit': amount * -1,
                        'quantity': 1,
                        'partner_id': rec.partner_id.id,
                        'company_id': rec.company_id.id,
                        'tax_ids': [(6, 0, product.taxes_id.ids)],
                    }
                    new_line = new_lines.new(vals)
                    new_line.account_id = new_line._get_computed_account()
                    new_line.recompute_tax_line = True
                    new_line._onchange_price_subtotal()
                    rec._recompute_dynamic_lines()

                elif rec.amount_discount > 0:
                    new_lines.update({'price_unit': rec.amount_discount * -1})
                    new_lines.recompute_tax_line = True
                    rec._recompute_dynamic_lines()

    def _update_discount(self):
        """
        Funcion para poder realizar la actualizacion de descuentos en Facturas
        :return:
        """
        invoices = self.env['account.move'].search([
            ('amount_des', '>', 0),
        ])
        facturas = []
        count = 0
        for i in invoices:
            count += 1
            sum_discount = 0
            disc2 = 0
            discount = i.amount_des
            total = i.amount_open
            lines = i.invoice_line_ids.filtered(lambda x: x.product_id.id != 5381 and x.product_id.id is not False)
            for l in lines:
                sum_discount += l.total_discount
            sum_discount = round(sum_discount, 2)
            percentage = (discount * 100) / total
            value = discount - sum_discount
            percentage = round(percentage, 2)
            if not(value < 0.5 and value > -0.5):
                if len(lines) == 1:
                    lines.disc = percentage
                    lines.total_discount = discount
                else:
                    for l in lines:
                        d2 = 0
                        d2 += (l.price_unit * (percentage / 100)) * l.quantity
                        l.disc = percentage
                        l.total_discount = d2
                        disc2 += d2
                        disc2 = round(disc2, 2)
                    value2 = discount - disc2
                    if value2 > 0:
                        lines[0].total_discount += value2
                    elif value2 < 0:
                        lines[0].total_discount += value2
                i.global_discount_rate = round(percentage, 2)
                self.env.cr.commit()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    disc = fields.Float('Descuento %', default=0.00)
    total_discount = fields.Float('Subtotal ', default=0.00)

    @api.onchange('quantity', 'price_unit', 'disc')
    def onchange_line(self):
        for r in self:
            if r.move_id.global_discount_type == 'percent':
                r.total_discount = round((r.price_unit * (r.disc/100)) * r.quantity, 2)

