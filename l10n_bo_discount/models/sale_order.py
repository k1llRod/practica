from odoo import fields, models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

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
        for line in self.order_line:
            line.update({
                'disc': self.global_discount_rate
            })
            line.onchange_line()
        self.calculate_discount_line()

    @api.onchange("cal_discount")
    def calculate_discount_line(self):
        new_lines = self.env['sale.order.line']
        ban_desc = True
        for rec in self:
            total_discount = 0
            line_discount = rec.order_line.filtered(lambda x: x.product_id.product_discount is True)
            lines = rec.order_line.filtered(lambda x: x.product_id.product_discount is False)
            for l in lines:
                total_discount += l.total_discount
            if line_discount:
                line_discount.price_unit = total_discount * -1
            rec.amount_discount = total_discount
            if rec.amount_discount > 0:
                currency = rec.currency_id
                for line in rec.order_line:
                    if line.product_id.product_discount:
                        ban_desc = False
                        new_lines = line
                        break
                if ban_desc and rec.amount_discount > 0:
                    product = rec.company_id.sales_discount_product
                    amount = rec.amount_discount
                    vals = {
                        'sequence': 10000,
                        'name': 'Descuento sobre las ventas',
                        'order_id': rec.id,
                        'currency_id': currency and currency.id or False,
                        'product_uom': product.uom_id.id,
                        'product_id': product.id,
                        'price_unit': amount * -1,
                        'product_uom_qty': 1,
                        'company_id': rec.company_id.id,
                        'tax_id': [(6, 0, product.taxes_id.ids)],
                    }
                    new_line = new_lines.new(vals)

                elif rec.amount_discount > 0:
                    new_lines.update({'price_unit': rec.amount_discount * -1})


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    disc = fields.Float('Descuento %', default=0.00)
    total_discount = fields.Float('Subtotal ', default=0.00)

    @api.onchange('product_uom_qty', 'price_unit', 'disc')
    def onchange_line(self):
        for r in self:
            if r.order_id.global_discount_type == 'percent':
                r.total_discount = round((r.price_unit * (r.disc / 100)) * r.product_uom_qty, 2)

    def _prepare_invoice_line(self, **optional_values):
        invoice_line = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)
        invoice_line['disc'] = self.disc
        invoice_line['total_discount'] = self.total_discount
        return invoice_line