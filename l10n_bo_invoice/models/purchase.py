from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    discount_total = fields.Monetary(string='Descuento Total',
                                     compute='_amount_all_qty',)
    amount_ice = fields.Monetary(string='Importe I.C.E. ',
                                 compute='_amount_all_qty',
                                 readonly=True,
                                 tracking=True,)
    amount_ali_esp = fields.Monetary('Importe I.C.E.',
                                     compute='_amount_all_qty',
                                     default=0.0)
    amount_ali_por = fields.Monetary('Importe I.C.E. %',
                                     compute='_amount_all_qty',
                                     default=0.0)
    volume_total = fields.Float('Total Litros',
                                store=True,
                                readonly=True,
                                compute='_compute_amount_all_qty',
                                tracking=True,)
    weight_total = fields.Float('Total Peso',
                                store=True,
                                readonly=True,
                                compute='_compute_amount_all_qty',
                                tracking=True)

    @api.depends('order_line.product_uom_qty')
    def _compute_amount_all_qty(self):
        for order in self:
            volumen = 0
            peso = 0
            for line in order.order_line:
                volumen += line.product_volume
                peso += line.product_weight
            order.volume_total = volumen
            order.weight_total = peso

    @api.depends('order_line.discount_amount',
                 'order_line.amount_ali_esp',
                 'order_line.amount_ali_por')
    def _amount_all_qty(self):
        for order in self:
            ice_esp = 0.0
            ice_por = 0.0
            disc = 0.0
            for line in order.order_line:
                ice_esp += line.amount_ali_esp
                ice_por += line.amount_ali_por
                disc += line.discount_amount
            order.discount_total = disc
            order.amount_ali_esp = ice_esp
            order.amount_ali_por = ice_por
            order.amount_ice = ice_esp + ice_por

    # ----UNIVERSAL DISCOUNT----
    global_discount_type = fields.Selection([('percent', 'Percentage'), ('amount', 'Amount')],
                                            string='Universal Discount Type', readonly=True,
                                            states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
                                            default='percent')
    global_discount_rate = fields.Float('Universal Discount ', readonly=True,
                                        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})
    amount_discount = fields.Monetary(string='Universal Discount', readonly=True, compute='_amount_all',
                                      tracking=True, store=True)
    enable_discount = fields.Boolean(compute='verify_discount')

    @api.depends('company_id.enable_discount')
    def verify_discount(self):
        for rec in self:
            rec.enable_discount = rec.company_id.enable_discount

    def action_view_invoice(self, invoices=False):
        res = super(PurchaseOrder, self).action_view_invoice()
        # for rec in self:
        # res['context']['default_global_discount_rate'] = rec.global_discount_rate
        # res['context']['default_global_discount_type'] = rec.global_discount_type
        return res

    @api.onchange('global_discount_rate', 'global_discount_type')
    def calculate_discount(self):
        new_lines = self.env['purchase.order.line']
        ban_desc = True
        for rec in self:
            if rec.global_discount_type == "amount":
                rec.amount_discount = rec.global_discount_rate if rec.amount_untaxed > 0 else 0
            elif rec.global_discount_type == "percent":
                if rec.global_discount_rate != 0.0:
                    rec.amount_discount = (rec.amount_untaxed + rec.amount_tax) * rec.global_discount_rate / 100
                else:
                    rec.amount_discount = 0
            elif not rec.global_discount_type:
                rec.amount_discount = 0
                rec.global_discount_rate = 0

            if rec.amount_discount > 0:
                for line in rec.order_line:
                    if line.product_id.product_discount:
                        ban_desc = False
                        new_lines = line
                        break
                if ban_desc and rec.amount_discount > 0:
                    vals = {
                        'product_id': rec.company_id.purchase_discount_product,
                        'product_uom': rec.company_id.purchase_discount_product.uom_id,
                        'product_qty': 1,
                        'price_unit': rec.amount_discount * -1,
                        'name': rec.company_id.purchase_discount_product.name,
                        'order_id': rec.id,
                        'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        'taxes_id': [(6, 0, rec.company_id.purchase_discount_product.supplier_taxes_id.ids)],
                    }
                    new_line = new_lines.new(vals)
                    new_lines = new_line
                elif rec.amount_discount > 0:
                    new_lines.write({'price_unit': rec.amount_discount * -1})
            else:
                for line in rec.order_line:
                    if line.product_id.product_discount:
                        ban_desc = False
                        new_lines = line
                        break
                new_lines.unlink()
            # rec.amount_total = rec.amount_tax + rec.amount_untaxed - rec.amount_discount

    @api.constrains('global_discount_rate')
    def check_discount_value(self):
        if self.global_discount_type == "percent":
            if self.global_discount_rate > 100 or self.global_discount_rate < 0:
                raise ValidationError('You cannot enter percentage value greater than 100.')
        else:
            if self.global_discount_rate < 0 or self.global_discount_rate > self.amount_untaxed:
                raise ValidationError(
                    'You cannot enter discount amount greater than actual cost or value lower than 0.')


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    discount_amount = fields.Monetary('Monto Descuento')
    amount_ali_esp = fields.Monetary('Importe I.C.E.')
    amount_ali_por = fields.Monetary('Importe I.C.E. %')
    product_volume = fields.Float(string='Volumen Litros', digits='Volume', compute='_compute_product_uom_qty',
                                  store=True)
    product_weight = fields.Float(string='Peso', digits='Stock Weight', compute='_compute_product_uom_qty', store=True)

    @api.depends('product_uom', 'product_qty', 'product_id.uom_id')
    def _compute_product_uom_qty(self):
        for line in self:
            if line.product_id and line.product_id.uom_id != line.product_uom:
                line.product_uom_qty = line.product_uom._compute_quantity(line.product_qty, line.product_id.uom_id)
            else:
                line.product_uom_qty = line.product_qty

            # Aplicar Unidades Alicuotas
            volumen = line.product_uom_qty * line.product_id.volume * 1000
            peso = line.product_uom_qty * line.product_id.weight
            line.product_volume = volumen
            line.product_weight = peso

    def _get_stock_move_price_unit(self):
        price_unit = super(PurchaseOrderLine, self)._get_stock_move_price_unit()
        self.ensure_one()
        line = self[0]
        order = line.order_id
        price_unit = line.price_unit
        if self.product_uom_qty > 0:
            pri_esp = self.amount_ali_esp / self.product_uom_qty
            pri_por = self.amount_ali_por / self.product_uom_qty
            ice_tot = pri_esp + pri_por
            price_unit = price_unit - pri_esp - pri_por
        if line.taxes_id:
            valores = line.taxes_id.with_context(round=False).compute_all(
                price_unit, currency=line.order_id.currency_id, quantity=1.0, product=line.product_id,
                partner=line.order_id.partner_id)
            price_unit = line.taxes_id.with_context(round=False).compute_all(
                price_unit, currency=line.order_id.currency_id, quantity=1.0, product=line.product_id,
                partner=line.order_id.partner_id
            )['total_void']
            price_unit = price_unit + ice_tot
        if line.product_uom.id != line.product_id.uom_id.id:
            price_unit *= line.product_uom.factor / line.product_id.uom_id.factor
        if order.currency_id != order.company_id.currency_id:
            price_unit = order.currency_id._convert(
                price_unit, order.company_id.currency_id, self.company_id, self.date_order or fields.Date.today(),
                round=False)
        # self.ensure_one()
        # if self.product_uom_qty > 0:
        #     pri_esp = self.amount_ali_esp / self.product_uom_qty
        #     pri_por = self.amount_ali_por / self.product_uom_qty
        #     price_unit = price_unit + pri_esp + pri_por
        return price_unit

    def _prepare_account_move_line(self, move=False):
        vals = super(PurchaseOrderLine, self)._prepare_account_move_line(move)
        vals['amount_ali_esp'] = self.amount_ali_esp
        vals['amount_ali_por'] = self.amount_ali_por
        vals['amount_ice_iehd'] = self.amount_ali_esp + self.amount_ali_por

        # ----UNIVERSAL DISCOUNT----
        if self.price_unit < 0 and self.product_id.type == 'service':
            vals['quantity'] = self.product_qty

        return vals

    # ----UNIVERSAL DISCOUNT----

    #     vals = super(PurchaseOrderLine, self)._prepare_account_move_line(move)
    #     if self.price_unit < 0 and self.product_id.type == 'service':
    #         vals['quantity'] = self.product_qty
    #     return vals
