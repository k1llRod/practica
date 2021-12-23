from odoo import api, fields, models, registry, _
from odoo.exceptions import UserError, ValidationError
import qrcode
import io
import base64
import datetime
from .operations.num_literal import to_word
import re


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('line_ids.balance', 'currency_id', 'company_id', 'invoice_date', 'line_ids')
    def _compute_amount_sin(self):
        amount_iva = 0
        amount_des = 0
        amount_exe = 0
        amount_ice = 0
        amount_open = 0
        for move in self:
            # if move.move_type != 'in_receipt':
            for bina in move.amount_by_group:
                amount_iva += bina[1]

            for line_inv in move.invoice_line_ids:
                if line_inv.price_unit > 0:
                    amount_open += line_inv.quantity * line_inv.price_unit
                else:
                    amount_des += line_inv.quantity * line_inv.price_unit

                if not line_inv.tax_ids:
                    amount_exe += line_inv.price_subtotal

                amount_ice += line_inv.amount_ice_iehd

            # amount_open = amount_open - amount_exe
            move.amount_iva = amount_iva
            move.amount_des = amount_des * -1
            move.amount_exe = amount_exe
            move.amount_ice_iehd = amount_ice
            move.amount_open = amount_open
            move.amount_imp = amount_open - amount_exe - amount_ice + amount_des

            #CONVERSION SEGUN TIPO DE CAMBIO
            if move.exchange_rate == 0:
                move.exchange_rate = 1
            move.amount_imp = move.amount_imp * move.exchange_rate
            move.amount_iva = move.amount_iva * move.exchange_rate
            move.amount_exe = move.amount_exe * move.exchange_rate
            move.amount_des = move.amount_des * move.exchange_rate
            move.amount_ice_iehd = move.amount_ice_iehd * move.exchange_rate
            move.amount_open = move.amount_open * move.exchange_rate

            # if amount_exe > 0:
            #     move.amount_iva = move.amount_imp * 0.13

    warehouse_id = fields.Many2one(comodel_name='stock.warehouse',
                                   string='Sucursal', readonly=True,
                                   states={'draft': [('readonly', False)]})
    date_time = fields.Datetime(string="Fecha/Hora", tracking=True)
    nit_ci = fields.Char(string='NIT/CI', size=12, default='0',
                         readonly=True, copy=True,
                         states={'draft': [('readonly', False)]})
    extension = fields.Char('Extensión', help="Usar sólo en CARNETS DE IDENTIDAD que tengan extensión.", readonly=True,
                            states={'draft': [('readonly', False)]})
    razon_social = fields.Char(string='Razón Social', size=100, default='S/N',
                               readonly=True, copy=True,
                               states={'draft': [('readonly', False)]})
    dosificacion = fields.Many2one(comodel_name='dosing.control',
                                   string='Certificado', readonly=True,
                                   states={'draft': [('readonly', False)]},
                                   help='Selecciona la dosificación en '
                                        'función de dos tipos:'
                                        'Manual o Computarizada')
    type_dosif = fields.Selection(related='dosificacion.type',
                                  string='Tipo de Dosificación')
    qr_text = fields.Char(string='Cadena Código QR', copy=False,
                          help='Puede poner sobre este campo un lector QR para que se distribuya los datos dentro de la factura')
    n_autorizacion = fields.Char(string='Nro. Autorización', size=15, tracking=True)
    n_factura = fields.Float(string='Nro. Factura', digits=(15, 0), default=0, copy=False, tracking=True)
    codigo_control = fields.Char(string='Código Control', size=100, default=0, copy=False, tracking=True,)
    qr_image = fields.Binary(string='Código QR', help='Imágen QR de la Factura',
                             readonly=True, copy=False,
                             states={'draft': [('readonly', False)]})
    amount_text = fields.Char(string="Monto Literal")
    state_sin = fields.Selection([
        ('A', 'ANULADA'),
        ('V', u'VÁLIDA'),
        ('E', 'EXTRAVIADA'),
        ('N', 'NO UTILIZADA'),
        ('C', 'EMITIDA EN CONTINGENCIA'),
        ('L', u'LIBRE CONSIGNACIÓN'),
        ('NA', u'NO APLICA'),
    ], "Estado SIN", help="Estado SIN", copy=False, default='V')
    n_dui = fields.Char(string=u"Nro. de DUI", size=16, default='0', tracking=True)
    note_credit_debit = fields.Boolean(string='Nota de Credito Debito',
                                       default=False, copy=False,
                                       readonly=True)
    tipo_com = fields.Selection([
        ('1',
         u'Compras para mercado interno con destino y actividades gravadas'),
        ('2',
         u'Compras para mercado interno con destino a actividades no gravadas'),
        ('3', u'Compras sujetas a proporcionalidad'),
        ('4', u'Compras para exportaciones'),
        (
            '5', u'Compras tanto para el mercado interno como para exportaciones'),
    ], "Tipo de Compra", help="Tipo de Compra", readonly=True, default='1',
        states={'draft': [('readonly', False)]})
    date_end = fields.Date(string="Límite emisión",
                           related="dosificacion.date_end",
                           help="Fecha Límite de emision para la dosificación asignada")

    # TOTALES
    amount_imp = fields.Monetary(string='Importe Base para Impuesto',
                                 currency_field='company_currency_id',
                                 compute='_compute_amount_sin',
                                 store=True, readonly=True,
                                 help='Importe base para crédito o débito fiscal')

    amount_iva = fields.Monetary(string='Importe IVA',
                                 store=True, readonly=True,
                                 compute='_compute_amount_sin',
                                 currency_field='company_currency_id',
                                 tracking=True)

    amount_exe = fields.Monetary(string='Importe Exento',
                                 currency_field='company_currency_id',
                                 store=True,
                                 compute='_compute_amount_sin', readonly=True)

    amount_des = fields.Monetary('Descuento',
                                 currency_field='company_currency_id',
                                 compute='_compute_amount_sin',
                                 store=True,
                                 readonly=True)

    amount_ice_iehd = fields.Monetary(string='Importe ICE/IEHD',
                                      currency_field='company_currency_id',
                                      store=True,
                                      compute='_compute_amount_sin',
                                      readonly=True)

    amount_open = fields.Monetary(string='Total Factura',
                                  currency_field='company_currency_id',
                                  compute='_compute_amount_sin',
                                  store=True, readonly=True,
                                  )
    print_original = fields.Boolean('Imprimir Original', copy=False, default=False, store=True)

    # Campos de Factura de importación
    invoice_import_flag = fields.Boolean(
        string="Factura Importacion",
        related='company_id.enable_invoice_import'
    )
    invoice_import = fields.Boolean(
        string='Factura de importación',
        default=False,
        tracking=True
    )

    # Campos de devengado
    accrued_expense_flag = fields.Boolean(default=lambda x: x.env['ir.config_parameter'].sudo().get_param(
                'l10n_bo_invoice.enable_accrued_expense') or False)
    accrued_expense = fields.Boolean(string='Devengado', default=False, tracking=True)

    @api.onchange('qr_text')
    def onchange_qr_text(self):
        if self.qr_text:
            s = self.qr_text
            ta = re.split(']|Ç|,|\*|\n',self.qr_text)
            # ta = s.split('|')
            n_fact = ta[1]
            n_aut = ta[2]
            cc_control = ta[6].replace('\'','-')
            fecha = ta[3].replace('-','/')
            fech = datetime.datetime.strptime(fecha, '%d/%m/%Y')
            fec = fech.date()
            self.n_autorizacion = n_aut
            self.n_factura = n_fact
            self.codigo_control = cc_control
            self.invoice_date = fec

    @api.onchange('warehouse_id')
    def onchange_warehouse_id(self):
        for invoice in self:
            if invoice.warehouse_id:
                invoice.dosificacion = invoice.warehouse_id.dosificacion.id
                invoice.n_autorizacion = invoice.warehouse_id.dosificacion.n_autorizacion

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        for invoice in self:
            if invoice.partner_id:
                invoice.extension = invoice.partner_id.extension
                if invoice.partner_id.razon_social:
                    invoice.razon_social = invoice.partner_id.razon_social
                else:
                    invoice.razon_social = 'S/N'
                if invoice.partner_id.nit_ci:
                    invoice.nit_ci = invoice.partner_id.nit_ci
                else:
                    invoice.nit_ci = '0'

    @api.onchange('dosificacion')
    def onchange_dosificacion(self):
        for invoice in self:
            if invoice.dosificacion:
                invoice.n_autorizacion = invoice.dosificacion.n_autorizacion

    def action_print_original(self):
        self.ensure_one()
        # if self.env.user.has_group('account.group_account_manager') and not self.print_original:
        report_name = 'l10n_bo_invoice.report_invoice_bol_original'
        # self.print_original = True
        # else:
        #     report_name = 'l10n_bo_invoice.report_invoice_bol_copia'

        return self.env['ir.actions.report'].search(
            [
                ('report_name', '=', report_name),
                ('report_type', '=', 'qweb-pdf')
            ], limit=1
        ).report_action(self)

    def action_invoice_print(self):
        if any(not move.is_invoice(include_receipts=True) for move in self):
            raise UserError(_("Only invoices could be printed."))

        self.filtered(lambda inv: not inv.invoice_sent).write(
            {'invoice_sent': True})
        if self.user_has_groups('account.group_account_invoice'):
            return self.env.ref(
                'l10n_bo_account_invoice.account_invoices_bol_original').report_action(
                self)
        else:
            return self.env.ref(
                'account.account_invoices_without_payment').report_action(self)

    def _recompute_tax_lines(self, recompute_tax_base_amount=False):
        ''' Compute the dynamic tax lines of the journal entry.
        :param lines_map: The line_ids dispatched by type containing:
            * base_lines: The lines having a tax_ids set.
            * tax_lines: The lines having a tax_line_id set.
            * terms_lines: The lines generated by the payment terms of the invoice.
            * rounding_lines: The cash rounding lines of the invoice.
        '''
        self.ensure_one()
        in_draft_mode = self != self._origin

        def _serialize_tax_grouping_key(grouping_dict):
            ''' Serialize the dictionary values to be used in the taxes_map.
            :param grouping_dict: The values returned by '_get_tax_grouping_key_from_tax_line' or '_get_tax_grouping_key_from_base_line'.
            :return: A string representing the values.
            '''
            return '-'.join(str(v) for v in grouping_dict.values())

        def _compute_base_line_taxes(base_line):
            ''' Compute taxes amounts both in company currency / foreign currency as the ratio between
            amount_currency & balance could not be the same as the expected currency rate.
            The 'amount_currency' value will be set on compute_all(...)['taxes'] in multi-currency.
            :param base_line:   The account.move.line owning the taxes.
            :return:            The result of the compute_all method.
            '''
            move = base_line.move_id

            if move.is_invoice(include_receipts=True):
                handle_price_include = True
                sign = -1 if move.is_inbound() else 1
                quantity = base_line.quantity
                if base_line.currency_id:
                    price_unit_foreign_curr = sign * base_line.price_unit * (1 - (base_line.discount / 100.0))
                    price_unit_foreign_curr = price_unit_foreign_curr - base_line.amount_ice_iehd / quantity
                    price_unit_comp_curr = base_line.currency_id._convert(price_unit_foreign_curr,
                                                                          move.company_id.currency_id, move.company_id,
                                                                          move.date, round=False)
                else:
                    price_unit_foreign_curr = 0.0
                    price_unit_comp_curr = sign * base_line.price_unit * (1 - (base_line.discount / 100.0))
                    price_unit_comp_curr = price_unit_comp_curr - base_line.amount_ice_iehd / quantity
                tax_type = 'sale' if move.move_type.startswith('out_') else 'purchase'
                is_refund = move.move_type in ('out_refund', 'in_refund')
            else:
                handle_price_include = False
                quantity = 1.0
                price_unit_foreign_curr = base_line.amount_currency
                price_unit_comp_curr = base_line.balance
                tax_type = base_line.tax_ids[0].type_tax_use if base_line.tax_ids else None
                is_refund = (tax_type == 'sale' and base_line.debit) or (tax_type == 'purchase' and base_line.credit)

            balance_taxes_res = base_line.tax_ids._origin.with_context(
                force_sign=move._get_tax_force_sign()).compute_all(
                price_unit_comp_curr,
                currency=base_line.company_currency_id,
                quantity=quantity,
                product=base_line.product_id,
                partner=base_line.partner_id,
                is_refund=is_refund,
                handle_price_include=handle_price_include,
            )

            if move.move_type == 'entry':
                repartition_field = is_refund and 'refund_repartition_line_ids' or 'invoice_repartition_line_ids'
                repartition_tags = base_line.tax_ids.flatten_taxes_hierarchy().mapped(repartition_field).filtered(
                    lambda x: x.repartition_type == 'base').tax_tag_ids
                tags_need_inversion = (tax_type == 'sale' and not is_refund) or (tax_type == 'purchase' and is_refund)
                if tags_need_inversion:
                    balance_taxes_res['base_tags'] = base_line._revert_signed_tags(repartition_tags).ids
                    for tax_res in balance_taxes_res['taxes']:
                        tax_res['tax_tag_ids'] = base_line._revert_signed_tags(
                            self.env['account.account.tag'].browse(tax_res['tax_tag_ids'])).ids

            if base_line.currency_id:
                # Multi-currencies mode: Taxes are computed both in company's currency / foreign currency.
                amount_currency_taxes_res = base_line.tax_ids._origin.with_context(
                    force_sign=move._get_tax_force_sign()).compute_all(
                    price_unit_foreign_curr,
                    currency=base_line.currency_id,
                    quantity=quantity,
                    product=base_line.product_id,
                    partner=base_line.partner_id,
                    is_refund=self.move_type in ('out_refund', 'in_refund'),
                    handle_price_include=handle_price_include,
                )

                if move.move_type == 'entry':
                    repartition_field = is_refund and 'refund_repartition_line_ids' or 'invoice_repartition_line_ids'
                    repartition_tags = base_line.tax_ids.mapped(repartition_field).filtered(
                        lambda x: x.repartition_type == 'base').tax_tag_ids
                    tags_need_inversion = (tax_type == 'sale' and not is_refund) or (
                            tax_type == 'purchase' and is_refund)
                    if tags_need_inversion:
                        balance_taxes_res['base_tags'] = base_line._revert_signed_tags(repartition_tags).ids
                        for tax_res in balance_taxes_res['taxes']:
                            tax_res['tax_tag_ids'] = base_line._revert_signed_tags(
                                self.env['account.account.tag'].browse(tax_res['tax_tag_ids'])).ids

                for b_tax_res, ac_tax_res in zip(balance_taxes_res['taxes'], amount_currency_taxes_res['taxes']):
                    tax = self.env['account.tax'].browse(b_tax_res['id'])
                    b_tax_res['amount_currency'] = ac_tax_res['amount']

                    # A tax having a fixed amount must be converted into the company currency when dealing with a
                    # foreign currency.
                    if tax.amount_type == 'fixed':
                        b_tax_res['amount'] = base_line.currency_id._convert(b_tax_res['amount'],
                                                                             move.company_id.currency_id,
                                                                             move.company_id, move.date)

            return balance_taxes_res

        taxes_map = {}

        # ==== Add tax lines ====
        to_remove = self.env['account.move.line']
        for line in self.line_ids.filtered('tax_repartition_line_id'):
            grouping_dict = self._get_tax_grouping_key_from_tax_line(line)
            grouping_key = _serialize_tax_grouping_key(grouping_dict)
            if grouping_key in taxes_map:
                # A line with the same key does already exist, we only need one
                # to modify it; we have to drop this one.
                to_remove += line
            else:
                taxes_map[grouping_key] = {
                    'tax_line': line,
                    'balance': 0.0,
                    'amount_currency': 0.0,
                    'tax_base_amount': 0.0,
                    'grouping_dict': False,
                }
        self.line_ids -= to_remove

        # ==== Mount base lines ====
        for line in self.line_ids.filtered(lambda line: not line.tax_repartition_line_id):
            # Don't call compute_all if there is no tax.
            if not line.tax_ids:
                line.tax_tag_ids = [(5, 0, 0)]
                continue

            compute_all_vals = _compute_base_line_taxes(line)

            # Assign tags on base line
            line.tax_tag_ids = compute_all_vals['base_tags'] or [(5, 0, 0)]

            tax_exigible = True
            for tax_vals in compute_all_vals['taxes']:
                grouping_dict = self._get_tax_grouping_key_from_base_line(line, tax_vals)
                grouping_key = _serialize_tax_grouping_key(grouping_dict)

                tax_repartition_line = self.env['account.tax.repartition.line'].browse(
                    tax_vals['tax_repartition_line_id'])
                tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id

                if tax.tax_exigibility == 'on_payment':
                    tax_exigible = False

                taxes_map_entry = taxes_map.setdefault(grouping_key, {
                    'tax_line': None,
                    'balance': 0.0,
                    'amount_currency': 0.0,
                    'tax_base_amount': 0.0,
                    'grouping_dict': False,
                })
                taxes_map_entry['balance'] += tax_vals['amount']
                taxes_map_entry['amount_currency'] += tax_vals.get('amount_currency', 0.0)
                taxes_map_entry['tax_base_amount'] += self._get_base_amount_to_display(tax_vals['base'],
                                                                                       tax_repartition_line,
                                                                                       tax_vals['group'])
                taxes_map_entry['grouping_dict'] = grouping_dict
            line.tax_exigible = tax_exigible

        # ==== Process taxes_map ====
        for taxes_map_entry in taxes_map.values():
            # Don't create tax lines with zero balance.
            if self.currency_id.is_zero(taxes_map_entry['balance']) and self.currency_id.is_zero(
                    taxes_map_entry['amount_currency']):
                taxes_map_entry['grouping_dict'] = False

            tax_line = taxes_map_entry['tax_line']

            if not tax_line and not taxes_map_entry['grouping_dict']:
                continue
            elif tax_line and not taxes_map_entry['grouping_dict']:
                # The tax line is no longer used, drop it.
                self.line_ids -= tax_line
            elif tax_line and recompute_tax_base_amount:
                tax_line.tax_base_amount = taxes_map_entry['tax_base_amount']
            elif tax_line:
                tax_line.update({
                    'amount_currency': taxes_map_entry['amount_currency'],
                    'debit': taxes_map_entry['balance'] > 0.0 and taxes_map_entry['balance'] or 0.0,
                    'credit': taxes_map_entry['balance'] < 0.0 and -taxes_map_entry['balance'] or 0.0,
                    'tax_base_amount': taxes_map_entry['tax_base_amount'],
                })
            else:
                create_method = in_draft_mode and self.env['account.move.line'].new or self.env[
                    'account.move.line'].create
                tax_repartition_line_id = taxes_map_entry['grouping_dict']['tax_repartition_line_id']
                tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_repartition_line_id)
                tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id
                tax_line = create_method({
                    'name': tax.name,
                    'move_id': self.id,
                    'partner_id': line.partner_id.id,
                    'company_id': line.company_id.id,
                    'company_currency_id': line.company_currency_id.id,
                    'quantity': 1.0,
                    'date_maturity': False,
                    'amount_currency': taxes_map_entry['amount_currency'],
                    'debit': taxes_map_entry['balance'] > 0.0 and taxes_map_entry['balance'] or 0.0,
                    'credit': taxes_map_entry['balance'] < 0.0 and -taxes_map_entry['balance'] or 0.0,
                    'tax_base_amount': taxes_map_entry['tax_base_amount'],
                    'exclude_from_invoice_tab': True,
                    'tax_exigible': tax.tax_exigibility == 'on_invoice',
                    **taxes_map_entry['grouping_dict'],
                })

            if in_draft_mode:
                tax_line._onchange_amount_currency()
                tax_line._onchange_balance()

    def _post(self, soft=True):
        res = super(AccountMove, self)._post()
        for invoice in self:
            if invoice.move_type in ('out_invoice') and invoice.type_dosif == 'automatica':
                dosif = invoice.dosificacion

                # Validaciones
                if not dosif:
                    raise Warning(_('Certificado de Autorización no Seleccionado'))
                if not invoice.warehouse_id:
                    raise Warning(_('Debe seleccionar una sucursal'))
                if not invoice.invoice_date:
                    raise ValidationError(_(
                        'Debe registrar la fecha de la factura'))
                if not invoice.nit_ci and not invoice.razon_social:
                    raise ValidationError(_(
                        'Debe registrar NIT/CI o Razón Social para facturar'))
                if invoice.invoice_date > dosif.date_end:
                    raise ValidationError(_(
                        'Fecha limite de dosificación superado, registre una nueva dosificación'))
                if invoice.nit_ci == '0' and (
                        invoice.razon_social in ('S/N', 's/n',
                                                 'sin nombre')) and invoice.amount_open > invoice.company_id.amount_valid:
                    raise ValidationError(_(
                        'El monto de la factura no esta permitido para las facturas con\nRazon Social = S/N y NIT o CI = 0'))
                # END Validaciones

                # Obtener datos para hacer la dosificacion
                nit_ci_em = invoice.warehouse_id.company_id.nit_ci
                n_factura = str(dosif.n_factura_actual)
                n_autorizacion = dosif.n_autorizacion
                if invoice.company_id.currency_id.name == 'BOB':
                    monto = invoice.amount_open
                    monto_invoice = invoice.amount_imp
                    descuento = invoice.amount_des
                    ice_iehd = invoice.amount_ice_iehd
                    exe = invoice.amount_exe
                elif invoice.company_id.currency_id.name == 'USD':
                    monto = float(invoice.amount_open) * float(invoice.tasa_cambio)
                    monto_invoice = float(invoice.amount_imp) * float(invoice.tasa_cambio)
                    descuento = float(invoice.amount_des) * float(invoice.tasa_cambio)
                    ice_iehd = float(invoice.amount_ice_iehd) * float(invoice.tasa_cambio)
                    exe = float(invoice.amount_exe) * float(invoice.tasa_cambio)
                nit_ci = invoice.nit_ci
                razon = invoice.razon_social
                fecha = invoice.invoice_date.strftime('%d/%m/%Y')
                cod_control = dosif.get_codigo_control(n_factura, nit_ci,
                                                       invoice.invoice_date,
                                                       monto)
                monto_qr = "{:.2f}".format(monto, 2)
                monto_invoice_qr = "{:.2f}".format(monto_invoice, 2)

                if descuento > 0:
                    monto_descuento = "{:.2f}".format(descuento, 2)
                else:
                    monto_descuento = 0

                if ice_iehd > 0:
                    monto_ice_iehd = "{:.2f}".format(ice_iehd, 2)
                else:
                    monto_ice_iehd = 0

                if exe > 0:
                    monto_exe = "{:.2f}".format(exe, 2)
                else:
                    monto_exe = 0

                qr_string = str(nit_ci_em) + '|' + str(n_factura) + '|' + str(
                    n_autorizacion) + '|' + str(
                    fecha) + '|' + str(monto_qr) + '|' + str(
                    monto_invoice_qr) + '|' + str(
                    cod_control) + '|' + str(
                    nit_ci) + '|' + str(monto_ice_iehd) + '|0|' + str(
                    monto_exe) + '|' + str(monto_descuento) + ''
                qr = qrcode.QRCode()
                qr.add_data(qr_string.encode('utf-8'))
                qr.make(fit=True)
                img = qr.make_image()
                buffer = io.BytesIO()
                img.save(buffer, format="PNG")
                img_str = base64.b64encode(buffer.getvalue())

                dosif.plus_factura()  # Siguiente Factura

                moneda = ' BOLIVIANOS'
                if invoice.currency_id.name == 'BOB':
                    texto = to_word(invoice.amount_total) + moneda
                # elif invoice.currency_id.name == 'USD':
                #     texto = to_word(float(invoice.amount_total) * float(invoice.tasa_cambio)) + moneda
                else:
                    texto = ""
                txt = str(texto).upper()
                invoice.write({'amount_text': txt,
                               'n_factura': n_factura,
                               'codigo_control': cod_control,
                               'qr_image': img_str,
                               'state_sin': 'V',
                               'invoice_date': datetime.datetime.now(),
                               'date_time': datetime.datetime.now()})

            elif invoice.move_type in ('in_receipt', 'out_receipt'):
                invoice.state_sin = 'NA'

            else:
                invoice.state_sin = 'V'
                moneda = ' BOLIVIANOS'
                if invoice.currency_id.name == 'BOB':
                    texto = to_word(invoice.amount_total) + moneda
                # elif invoice.currency_id.name == 'USD' and invoice.tasa_cambio:
                #     texto = to_word(float(invoice.amount_total) * float(invoice.tasa_cambio)) + moneda
                else:
                    texto = ""
                txt = str(texto).upper()
                invoice.amount_text = txt
        return res

    @api.constrains('n_factura', 'invoice_date')
    def _check_nivel_factura(self):
        for inv in self:
            if inv.type_dosif == 'automatica':
                if inv.n_factura != 0:
                    val = inv.search_count(
                        [('invoice_date', '>', inv.invoice_date),
                         ('company_id', '=', inv.company_id.id),
                         ('n_factura', '>', inv.n_factura)])
                    if val > 1:
                        raise ValidationError(_(
                            "La factura que esta tratando de generar tiene fecha menor a una factura ya valida en el sistema"))

    @api.constrains('n_autorizacion', 'n_factura')
    def _check_factura_sin(self):
        for inv in self:
            if inv.move_type in ('in_invoice', 'in_refund'):
                if inv.n_factura != 0 and inv.n_autorizacion != '':
                    val = inv.search_count(
                        [('n_factura', '=', inv.n_factura),
                         ('company_id', '=', inv.company_id.id),
                         ('n_autorizacion', '=', inv.n_autorizacion)])
                    if val > 1:
                        raise ValidationError(_(
                            "Ya tiene registrado el Nro de Factura y Nro de Autorización en el sistema"))

    def button_draft(self):
        res = super(AccountMove, self).button_draft()
        for move in self:
            move.state_sin = 'NA'
        return res

    def button_cancel(self):
        res = super(AccountMove, self).button_cancel()
        for move in self:
            move.state_sin = 'NA'
        return res

    # ----UNIVERSAL DISCOUNT----
    global_discount_type = fields.Selection([
        ('percent', 'Percentage'),
        ('amount', 'Amount')],
        string='Descuento Universal Type',
        readonly=True,
        states={'draft': [('readonly', False)],
                'sent': [('readonly', False)]},
        default='percent')
    global_discount_rate = fields.Float(string='Descuento universal',
                                        readonly=True,
                                        states={'draft': [('readonly', False)],
                                                'sent': [('readonly', False)]})
    amount_discount = fields.Monetary(string='Descuento Universal',
                                      readonly=True,
                                      compute='_compute_amount',
                                      store=True, tracking=True)
    enable_discount = fields.Boolean(compute='verify_discount')
    sales_discount_product_id = fields.Integer(compute='verify_discount')
    purchase_discount_product_id = fields.Integer(compute='verify_discount')

    @api.depends('company_id.enable_discount')
    def verify_discount(self):
        for rec in self:
            rec.enable_discount = rec.company_id.enable_discount
            rec.sales_discount_product_id = rec.company_id.sales_discount_product.id
            rec.purchase_discount_product_id = rec.company_id.purchase_discount_product.id

    @api.onchange('global_discount_rate', 'global_discount_type')
    def calculate_discount(self):
        new_lines = self.env['account.move.line']
        ban_desc = True
        # if 'default_global_discount_rate' in self._context:
        #     return False
        for rec in self:
            if rec.global_discount_type == "amount":
                rec.amount_discount = rec.global_discount_rate if rec.amount_untaxed > 0 else 0
            elif rec.global_discount_type == "percent":
                if rec.global_discount_rate != 0.0:
                    rec.amount_discount = (rec.amount_untaxed + rec.amount_tax) * rec.global_discount_rate / 100
                else:
                    rec.amount_discount = 0
            elif not rec.global_discount_type:
                rec.global_discount_rate = 0
                rec.amount_discount = 0

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
                        'name': '%s: %s' % ('Descuento sobre las ventas', rec.name),
                        'move_id': rec.id,
                        # 'journal_id': rec.journal_id.id,
                        # 'move_id': rec._origin,
                        'currency_id': currency and currency.id or False,
                        'date_maturity': rec.invoice_date_due,
                        'product_uom_id': product.uom_id.id,
                        'product_id': product.id,
                        'price_unit': amount * -1,
                        'quantity': 1,
                        'partner_id': rec.partner_id.id,
                        'company_id': rec.company_id.id,
                        # 'analytic_account_id': self.account_analytic_id.id,
                        # 'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
                        'tax_ids': [(6, 0, product.taxes_id.ids)],
                        # 'display_type': 'none',
                    }
                    new_line = new_lines.new(vals)
                    new_line.account_id = new_line._get_computed_account()
                    new_line.recompute_tax_line = True
                    new_line._onchange_price_subtotal()
                    rec._recompute_dynamic_lines()
                    new_lines = new_line

                elif rec.amount_discount > 0:
                    new_lines.write({'price_unit': rec.amount_discount * -1})
                    new_lines.recompute_tax_line = True
                    rec._recompute_dynamic_lines()
            # else:
            #     for line in rec.invoice_line_ids:
            #         if line.product_id.product_discount:
            #             ban_desc = False
            #             new_lines = line
            #             break
            #     new_lines.unlink()

    @api.constrains('global_discount_rate')
    def check_discount_value(self):
        if self.global_discount_type == "percent":
            if self.global_discount_rate > 100 or self.global_discount_rate < 0:
                raise ValidationError(
                    'You cannot enter percentage value greater than 100.')
        else:
            if self.global_discount_rate < 0 or self.amount_untaxed < 0:
                raise ValidationError(
                    'You cannot enter discount amount greater than actual cost or value lower than 0.')

    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None,
                        description=None, journal_id=None):
        res = super(AccountMove, self)._prepare_refund(invoice, date_invoice=None,
                                                       date=None,
                                                       description=None,
                                                       journal_id=None)
        res['global_discount_rate'] = self.global_discount_rate
        res['global_discount_type'] = self.global_discount_type
        return res

    @api.model
    def accrued_alert(self, use_new_cursor=False):
        try:
            cr = registry(self._cr.dbname).cursor()
            self = self.with_env(self.env(cr=cr))
            group = self.env.ref('account.group_account_manager')
            usuario = group.users
            body_html = "<p><h3>Facturas Devengadas</h3></p>" \
                        "<table style='width:80%;border: 1px solid black;border-collapse: collapse;'>" \
                        "<tr>" \
                        "<td><strong>Factura</strong></td>" \
                        "<td><strong>Fecha</strong></td>" \
                        "<td><strong>Link</strong></td>" \
                        "</tr>"
            body_tr = ""

            sql_query = """select 
                                am.id,
                                am.name,
                                am.state,
                                am.invoice_date		
                            from account_move am
                            where am.move_type = 'in_invoice'
                            and am.accrued_expense = true
                            and am.state = 'posted'
                            and am.invoice_date >= date_trunc('month', current_date - interval '1' month)
                            and am.invoice_date < date_trunc('month', current_date)"""

            self.env.cr.execute(sql_query)
            val = 0
            ids_invoice=[]
            for line in self.env.cr.dictfetchall():
                body_tr = body_tr + """
                                            <tr>
                                            <td>""" + str(line.get('name')) + """</td>
                                            <td>""" + str(line.get('invoice_date')) + """</td>
                                            <td><a href=# data-oe-model=account.move data-oe-id=""" + str(
                    line.get('id')) + """>""" + str(line.get('name')) + """</a></td>
                                            </tr>
                                    """
                val = 1
                ids_invoice.append(line.get('id'))

            body_html_send = body_html + body_tr + "</table>"
            if val > 0:
                notification_ids=[]
                for d in self.env['res.users'].browse(1):
                    for us in usuario:
                        notification_ids.append((0, 0, {
                            'res_partner_id': us.partner_id.id,
                            'notification_type': 'inbox'}))

                    new_msg = d.message_post(body=body_html_send, message_type='comment',
                                                        subtype_id=self.env.ref('mail.mt_comment').id,
                                                        notification_ids=notification_ids)
                    new_msg.sudo().write({'notification_ids': notification_ids})
                    cr.commit()
        finally:
            if use_new_cursor:
                try:
                    self._cr.close()
                except Exception:
                    pass

        return True

    # TIPO DE CAMBIO
    exchange_rate = fields.Float(
        string='Tipo de Cambio',
        store=True,
    )

    @api.onchange('currency_id')
    def _onchange_currency_exchange_rate(self):
        rate = self.env['res.currency.rate'].search([
            ('currency_id', '=', self.currency_id.id)
        ], order='id DESC', limit=1)
        if rate:
            self.exchange_rate = self.env.company.currency_id.rate / rate.rate
        else:
            self.exchange_rate = 1
    # END TIPO DE CAMBIO

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    amount_ice_iehd = fields.Monetary(string='ICE/IEHD',
                                      default=0.0,
                                      help='Valor correspondiente al ICE, IEHD, Tasas y/o Contribuciones incluidas en la venta')
    amount_exe = fields.Monetary(
        string='Exento',
        default=0.0,
        help='Importe correspondiente a ventas por exportaciones de bienes y operaciones exentas.',
    )
    amount_ali_esp = fields.Monetary('Importe I.C.E.')
    amount_ali_por = fields.Monetary('Importe I.C.E. %')

    itf_or_commission = fields.Boolean(
        string='ITF O Comisión',
        default=False,
    )

    def write(self, vals):
        res = super(AccountMoveLine, self).write(vals)
        for line in self:
            if line.purchase_line_id and line.price_unit == 0:
                if line.price_unit != line.purchase_line_id.price_unit:
                    line.price_unit = line.purchase_line_id.price_unit
        return res

    @api.model_create_multi
    def create(self, vals_list):
        res = super(AccountMoveLine, self).create(vals_list)
        for ln in res:
            if ln.purchase_line_id:
                ln.amount_ali_esp = ln.purchase_line_id.amount_ali_esp
                ln.amount_ali_por = ln.purchase_line_id.amount_ali_por
                ln.amount_ice_iehd = ln.purchase_line_id.amount_ali_esp + ln.purchase_line_id.amount_ali_por
        return res

    @api.onchange('quantity', 'discount', 'price_unit', 'tax_ids',
                  'amount_ice_iehd')
    def _onchange_price_subtotal(self):
        for line in self:
            if not line.move_id.is_invoice(include_receipts=True):
                continue
            line.update(line._get_price_total_and_subtotal())
            line.update(line._get_fields_onchange_subtotal())

    @api.model
    def _get_price_total_and_subtotal_model(self, price_unit, quantity,
                                            discount, currency, product,
                                            partner, taxes,
                                            move_type):
        res = {}
        subtotal_ice = price_unit * quantity
        if move_type in ('out_invoice', 'out_refund'):
            res['amount_ali_esp'] = (product.volume * 1000 * quantity) * product.ali_esp
            res['amount_ali_por'] = (subtotal_ice - (subtotal_ice * 0.13)) * (product.ali_por / 100)
        else:
            res['amount_ali_esp'] = self.amount_ali_esp
            res['amount_ali_por'] = self.amount_ali_por
        if res['amount_ali_esp'] > 0 or res['amount_ali_por'] > 0:
            res['amount_ice_iehd'] = res['amount_ali_esp'] + res['amount_ali_por']
            price_unit_wo_discount = (price_unit * (1 - (discount / 100.0))) - res['amount_ali_esp'] / quantity - res[
                'amount_ali_por'] / quantity
        else:
            price_unit_wo_discount = price_unit * (1 - (discount / 100.0))
        # price_unit_wo_discount = price_unit * (1 - (discount / 100.0))
        subtotal = quantity * price_unit_wo_discount

        if taxes:
            force_sign = -1 if move_type in ('out_invoice', 'in_refund', 'out_receipt') else 1
            taxes_res = taxes._origin.with_context(force_sign=force_sign).compute_all(price_unit_wo_discount,
                                                                                      quantity=quantity,
                                                                                      currency=currency,
                                                                                      product=product, partner=partner,
                                                                                      is_refund=move_type in (
                                                                                          'out_refund', 'in_refund'))
            if res['amount_ali_esp'] > 0 or res['amount_ali_por'] > 0:
                res['price_subtotal'] = taxes_res['total_excluded'] + res['amount_ali_esp'] + res['amount_ali_por']
                res['price_total'] = taxes_res['total_included'] + res['amount_ali_esp'] + res['amount_ali_por']
            else:
                res['price_subtotal'] = taxes_res['total_excluded']
                res['price_total'] = taxes_res['total_included']
        else:
            res['price_total'] = res['price_subtotal'] = subtotal
        if currency:
            res = {k: currency.round(v) for k, v in res.items()}
        return res