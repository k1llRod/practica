from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    nit_ci = fields.Char(string=u"NIT/CI", size=12, readonly=True,
                         states={'draft': [('readonly', False)]}, copy=True,
                         default='0',
                         help='NIT o CI del Cliente, considere que la información de este campo sera utilizada para generar la factura computarizada')
    razon_social = fields.Char(string=u"Razón Social", size=100, readonly=True,
                               states={'draft': [('readonly', False)]},
                               copy=True, default='S/N',
                               help='Razón Social del Cliente, considere que la información de este campo sera utilizada para generar la factura computarizada')
    amount_ice = fields.Monetary(string='Importe I.C.E.', readonly=True,
                                 compute='_amount_all', store=True,
                                 tracking=True)
    extension = fields.Char('Extensión', help="Usar sólo en CARNETS DE IDENTIDAD que tengan extensión.",
                            readonly=True,states={'draft': [('readonly', False)]})


    @api.depends('order_line.price_total')
    def _amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = amount_ice = amount_desc = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
                amount_ice += (line.amount_ali_esp + line.amount_ali_por)
                if line.price_unit < 0:
                    amount_desc += line.price_unit * line.product_uom_qty
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax + amount_ice,
                'amount_ice': amount_ice,
                'amount_discount': amount_desc * -1,
            })

    # @api.onchange('partner_id')
    # def change_partner_sin(self):
    #     for order in self:
    #         if order.partner_id:
    #             order.razon_social = order.partner_id.razon_social
    #             order.nit_ci = order.partner_id.nit_ci
    #             order.extension = order.partner_id.extension

    @api.onchange('partner_invoice_id')
    def inst_data_invoice(self):
        for rec in self:
            rec.razon_social = rec.partner_invoice_id.razon_social
            rec.nit_ci = rec.partner_invoice_id.nit_ci
            rec.extension = rec.partner_invoice_id.extension

    def _prepare_invoice(self):
        ret = super(SaleOrder, self)._prepare_invoice()
        ret['warehouse_id'] = self.warehouse_id.id
        ret['dosificacion'] = self.warehouse_id.dosificacion.id
        ret['n_autorizacion'] = self.warehouse_id.dosificacion.n_autorizacion
        ret['razon_social'] = self.razon_social
        ret['nit_ci'] = self.nit_ci
        ret['extension'] = self.extension
        return ret

    @api.constrains('user_id')
    def change_warehouse(self):
        """En caso se tenga una sola compañía, se habilita el campo warehouse_id de res_user,
        En caso se tengan más compañías, la regla de almacén por defecto se cancela"""
        if len(self.env['res.company'].search([])) == 1:
            self.warehouse_id = self.user_id.warehouse_id


class SaleOrder2(models.Model):
    _inherit = 'sale.order'

    global_discount_type = fields.Selection(
        [('percent', 'Percentage'), ('amount', 'Amount')],
        string='Universal Discount Type',
        readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        default='percent')
    global_discount_rate = fields.Float('Universal discount',
                                        readonly=True,
                                        states={'draft': [('readonly', False)],
                                                'sent': [('readonly', False)]})
    amount_discount = fields.Monetary(string='Universal Discount',
                                      readonly=True, compute='_amount_all',
                                      store=True,
                                      tracking=True)
    enable_discount = fields.Boolean(compute='verify_discount')

    @api.depends('company_id.enable_discount')
    def verify_discount(self):
        for rec in self:
            rec.enable_discount = rec.company_id.enable_discount

    def _prepare_invoice(self):
        res = super(SaleOrder2, self)._prepare_invoice()
        for rec in self:
            res['global_discount_rate'] = rec.global_discount_rate
            res['global_discount_type'] = rec.global_discount_type
        return res

    @api.onchange('global_discount_rate', 'global_discount_type')
    def calculate_discount(self):
        new_lines = self.env['sale.order.line']
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
                        'sequence': 10000,
                        'product_id': rec.company_id.sales_discount_product,
                        'product_uom': rec.company_id.sales_discount_product.uom_id,
                        'product_uom_qty': 1,
                        'price_unit': rec.amount_discount * -1,
                        'name': rec.company_id.sales_discount_product.name,
                        'order_id': rec.id,
                        'tax_id': [(6, 0, rec.company_id.sales_discount_product.taxes_id.ids)],
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
            # rec.amount_total = rec.amount_untaxed + rec.amount_tax - rec.amount_discount

    @api.constrains('global_discount_rate')
    def check_discount_value(self):
        if self.global_discount_type == "percent":
            if self.global_discount_rate > 100 or self.global_discount_rate < 0:
                raise ValidationError(
                    'No puede ingresar un valor de porcentaje mayor que 100.')
        else:
            if self.global_discount_rate < 0 or self.global_discount_rate > self.amount_untaxed:
                raise ValidationError(
                    'No puede ingresar un monto de descuento mayor que el costo real o un valor menor a 0.')


class KsSaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def _create_invoice(self, order, so_line, amount):
        invoice = super(KsSaleAdvancePaymentInv, self)._create_invoice(order, so_line, amount)
        if invoice:
            invoice['global_discount_rate'] = order.global_discount_rate
            invoice['global_discount_type'] = order.global_discount_type
        return invoice


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    amount_ali_esp = fields.Monetary('Importe I.C.E.')
    amount_ali_por = fields.Monetary('Importe I.C.E. %')

    # Requerido para actualizar IVA

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        for line in self:
            subtotal = line.price_unit * line.product_uom_qty

            line.amount_ali_esp = (line.product_id.volume * 1000 * line.product_uom_qty) * line.product_id.ali_esp

            if line.product_uom_qty > 0:
                p_unit_esp = line.amount_ali_esp / line.product_uom_qty
                p_unit_por = line.amount_ali_por / line.product_uom_qty

            line.amount_ali_por = (subtotal - (subtotal * 0.13)) * (line.product_id.ali_por / 100)
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                            product=line.product_id, partner=line.order_id.partner_shipping_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })
            if self.env.context.get('import_file', False) and not self.env.user.user_has_groups(
                    'account.group_account_manager'):
                line.tax_id.invalidate_cache(['invoice_repartition_line_ids'], [line.tax_id.id])
