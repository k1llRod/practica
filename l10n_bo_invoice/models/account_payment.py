from odoo import api, fields, models, _

from odoo.exceptions import UserError, ValidationError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    amount_pay = fields.Monetary(string="Monto Pagado")
    amount_change = fields.Monetary(string="Cambio")

    amount_itf = fields.Float(
        string='Monto ITF',
        default=0.0,
        compute="amountITF"
    )

    amount_bank_commission = fields.Float(
        string='Monto comisión bancaria',
        default=0.0,
        compute="amountBankCommission"
    )

    @api.depends('journal_id')
    def amountITF(self):
        if self.journal_id.applicable_tax.name == 'ITF':
            self.amount_itf = self.journal_id.applicable_tax.amount
        else:
            self.amount_itf = 0.0

    @api.depends('journal_id','payment_type')
    def amountBankCommission(self):
        if self.journal_id.bank_commission_rate > 0 and self.payment_type == 'inbound':
            self.amount_bank_commission = self.journal_id.bank_commission_rate
        else:
            self.amount_bank_commission = 0.0

    @api.onchange('amount_pay', 'amount')
    def _onchange_amount_pay(self):
        for payment in self:
            if payment.amount > 0:
                payment.amount_change = payment.amount_pay - payment.amount

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        ''' Prepare the dictionary to create the default account.move.lines for the current payment.
        :param write_off_line_vals: Optional dictionary to create a write-off account.move.line easily containing:
            * amount:       The amount to be added to the counterpart amount.
            * name:         The label to set on the line.
            * account_id:   The account on which create the write-off.
        :return: A list of python dictionary to be passed to the account.move.line's 'create' method.
        '''
        self.ensure_one()
        write_off_line_vals = write_off_line_vals or {}

        if not self.journal_id.payment_debit_account_id or not self.journal_id.payment_credit_account_id:
            raise UserError(_(
                "You can't create a new payment without an outstanding payments/receipts account set on the %s journal.",
                self.journal_id.display_name))

        # Compute amounts.
        write_off_amount = write_off_line_vals.get('amount', 0.0)

        if self.payment_type == 'inbound':
            # Receive money.
            counterpart_amount = -self.amount
            write_off_amount *= -1
        elif self.payment_type == 'outbound':
            # Send money.
            counterpart_amount = self.amount
        else:
            counterpart_amount = 0.0
            write_off_amount = 0.0

        balance = self.currency_id._convert(counterpart_amount, self.company_id.currency_id, self.company_id, self.date)
        counterpart_amount_currency = counterpart_amount
        write_off_balance = self.currency_id._convert(write_off_amount, self.company_id.currency_id, self.company_id, self.date)
        write_off_amount_currency = write_off_amount
        currency_id = self.currency_id.id

        if self.is_internal_transfer:
            if self.payment_type == 'inbound':
                liquidity_line_name = _('Transfer to %s', self.journal_id.name)
            else: # payment.payment_type == 'outbound':
                liquidity_line_name = _('Transfer from %s', self.journal_id.name)
        else:
            liquidity_line_name = self.payment_reference

        # Compute a default label to set on the journal items.

        payment_display_name = {
            'outbound-customer': _("Customer Reimbursement"),
            'inbound-customer': _("Customer Payment"),
            'outbound-supplier': _("Vendor Payment"),
            'inbound-supplier': _("Vendor Reimbursement"),
        }

        default_line_name = self.env['account.move.line']._get_default_line_name(
            _("Internal Transfer") if self.is_internal_transfer else payment_display_name['%s-%s' % (self.payment_type, self.partner_type)],
            self.amount,
            self.currency_id,
            self.date,
            partner=self.partner_id,
        )
        if self.env['ir.config_parameter'].sudo().get_param('l10n_bo_invoice.lot_commission') and \
                self.journal_id.bank_commission_rate > 0 and self.payment_type == 'inbound':
            bank_rate = balance * self.journal_id.bank_commission_rate
            new_balance = balance - bank_rate
            new_counterpart_amount_currency = counterpart_amount_currency - (counterpart_amount_currency * self.journal_id.bank_commission_rate)
            line_vals_list = [
                # Liquidity line.
                {
                    'name': liquidity_line_name or default_line_name,
                    'date_maturity': self.date,
                    'amount_currency': -new_counterpart_amount_currency,
                    'currency_id': currency_id,
                    'debit': new_balance < 0.0 and -new_balance or 0.0,
                    'credit': new_balance > 0.0 and new_balance or 0.0,
                    'partner_id': self.partner_id.id,
                    'account_id': self.journal_id.commission_grouping_account_id.id if new_balance < 0.0 else self.journal_id.payment_credit_account_id.id,
                    'itf_or_commission': False,
                },
                # BANK COMMISSION RATE
                {
                    'name': liquidity_line_name or default_line_name,
                    'date_maturity': self.date,
                    'amount_currency': -counterpart_amount_currency * self.journal_id.bank_commission_rate,
                    'currency_id': currency_id,
                    'debit': bank_rate < 0.0 and -bank_rate or 0.0,
                    'credit': bank_rate > 0.0 and bank_rate or 0.0,
                    'partner_id': self.partner_id.id,
                    'account_id': self.journal_id.payment_credit_account_id.id,
                    'itf_or_commission': False,
                },
                # Receivable / Payable.
                {
                    'name': self.payment_reference or default_line_name,
                    'date_maturity': self.date,
                    'amount_currency': counterpart_amount_currency + write_off_amount_currency if currency_id else 0.0,
                    'currency_id': currency_id,
                    'debit': balance + write_off_balance > 0.0 and balance + write_off_balance or 0.0,
                    'credit': balance + write_off_balance < 0.0 and -balance - write_off_balance or 0.0,
                    'partner_id': self.partner_id.id,
                    'account_id': self.destination_account_id.id,
                    'itf_or_commission': False,
                },
            ]
        else:
            line_vals_list = [
                # Liquidity line.
                {
                    'name': liquidity_line_name or default_line_name,
                    'date_maturity': self.date,
                    'amount_currency': -counterpart_amount_currency,
                    'currency_id': currency_id,
                    'debit': balance < 0.0 and -balance or 0.0,
                    'credit': balance > 0.0 and balance or 0.0,
                    'partner_id': self.partner_id.id,
                    'account_id': self.journal_id.payment_debit_account_id.id if balance < 0.0 else self.journal_id.payment_credit_account_id.id,
                    'itf_or_commission': False,
                },
                # Receivable / Payable.
                {
                    'name': self.payment_reference or default_line_name,
                    'date_maturity': self.date,
                    'amount_currency': counterpart_amount_currency + write_off_amount_currency if currency_id else 0.0,
                    'currency_id': currency_id,
                    'debit': balance + write_off_balance > 0.0 and balance + write_off_balance or 0.0,
                    'credit': balance + write_off_balance < 0.0 and -balance - write_off_balance or 0.0,
                    'partner_id': self.partner_id.id,
                    'account_id': self.destination_account_id.id,
                    'itf_or_commission': False,
                },
            ]

        # ITF
        if self.journal_id.applicable_tax.name == 'ITF':
            imp_itf = (self.amount * self.journal_id.applicable_tax.amount)/100

            if self.payment_type == 'inbound':
                receivable_account_id = self.destination_account_id.id,
            elif self.payment_type == 'outbound':
                receivable_account_id = self.journal_id.payment_debit_account_id.id if balance < 0.0 else self.journal_id.payment_credit_account_id.id,

            # Liquidity line.
            line_vals_list.append({
                'name': 'ITF',
                'date_maturity': self.date,
                'amount_currency': -imp_itf,
                'currency_id': currency_id,
                'debit': imp_itf,
                'credit': 0.0,
                'partner_id': self.partner_id.id,
                'account_id': self.journal_id.applicable_tax.invoice_repartition_line_ids.account_id.id,
                'itf_or_commission': True,
            })
            # Receivable / Payable.
            line_vals_list.append({
                'name': 'ITF',
                'date_maturity': self.date,
                'amount_currency': imp_itf,
                'currency_id': currency_id,
                'debit': 0.0,
                'credit': imp_itf,
                'partner_id': self.partner_id.id,
                # 'account_id': self.destination_account_id.id,
                'account_id': receivable_account_id,
                'itf_or_commission': True,
            })
        # END ITF
        if write_off_balance:
            # Write-off line.
            line_vals_list.append({
                'name': write_off_line_vals.get('name') or default_line_name,
                'amount_currency': -write_off_amount_currency,
                'currency_id': currency_id,
                'debit': write_off_balance < 0.0 and -write_off_balance or 0.0,
                'credit': write_off_balance > 0.0 and write_off_balance or 0.0,
                'partner_id': self.partner_id.id,
                'account_id': write_off_line_vals.get('account_id'),
                'itf_or_commission': False,
            })
        return line_vals_list

    def _synchronize_from_moves(self, changed_fields):
        ''' Update the account.payment regarding its related account.move.
        Also, check both models are still consistent.
        :param changed_fields: A set containing all modified fields on account.move.
        '''
        if self._context.get('skip_account_move_synchronization'):
            return

        for pay in self.with_context(skip_account_move_synchronization=True):

            # After the migration to 14.0, the journal entry could be shared between the account.payment and the
            # account.bank.statement.line. In that case, the synchronization will only be made with the statement line.
            if pay.move_id.statement_line_id:
                continue

            move = pay.move_id
            move_vals_to_write = {}
            payment_vals_to_write = {}

            if 'journal_id' in changed_fields:
                if pay.journal_id.type not in ('bank', 'cash'):
                    raise UserError(_("A payment must always belongs to a bank or cash journal."))

            if 'line_ids' in changed_fields:
                all_lines = move.line_ids
                liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

                if (len(liquidity_lines) != 1 or len(counterpart_lines) != 1) \
                        and self.journal_id.applicable_tax.name != 'ITF' \
                        and self.journal_id.bank_commission_rate == 0:
                    raise UserError(_(
                        "The journal entry %s reached an invalid state relative to its payment.\n"
                        "To be consistent, the journal entry must always contains:\n"
                        "- one journal item involving the outstanding payment/receipts account.\n"
                        "- one journal item involving a receivable/payable account.\n"
                        "- optional journal items, all sharing the same account.\n\n"
                    ) % move.display_name)

                if writeoff_lines and len(writeoff_lines.account_id) != 1 and self.journal_id.applicable_tax.name != 'ITF':
                    raise UserError(_(
                        "The journal entry %s reached an invalid state relative to its payment.\n"
                        "To be consistent, all the write-off journal items must share the same account."
                    ) % move.display_name)

                if any(line.currency_id != all_lines[0].currency_id for line in all_lines):
                    raise UserError(_(
                        "The journal entry %s reached an invalid state relative to its payment.\n"
                        "To be consistent, the journal items must share the same currency."
                    ) % move.display_name)

                if any(line.partner_id != all_lines[0].partner_id for line in all_lines):
                    raise UserError(_(
                        "The journal entry %s reached an invalid state relative to its payment.\n"
                        "To be consistent, the journal items must share the same partner."
                    ) % move.display_name)

                if counterpart_lines.account_id.user_type_id.type == 'receivable':
                    partner_type = 'customer'
                else:
                    partner_type = 'supplier'
                if self.journal_id.applicable_tax.name == 'ITF':
                    if len(liquidity_lines) == 1:
                        liquidity_amount = liquidity_lines.amount_currency

                        move_vals_to_write.update({
                            'currency_id': liquidity_lines.currency_id.id,
                            'partner_id': liquidity_lines.partner_id.id,
                        })
                        payment_vals_to_write.update({
                            'amount': abs(liquidity_amount),
                            'partner_type': partner_type,
                            'currency_id': liquidity_lines.currency_id.id,
                            'destination_account_id': counterpart_lines.account_id.id,
                            'partner_id': liquidity_lines.partner_id.id,
                        })
                    elif len(liquidity_lines) > 1:
                        liquidity_amount = 0
                        for liq in liquidity_lines:
                            liquidity_amount += liq.amount_currency

                        move_vals_to_write.update({
                            'currency_id': liquidity_lines[0].currency_id.id,
                            'partner_id': liquidity_lines[0].partner_id.id,
                        })
                        payment_vals_to_write.update({
                            'amount': abs(liquidity_amount),
                            'partner_type': partner_type,
                            'currency_id': liquidity_lines[0].currency_id.id,
                            'destination_account_id': counterpart_lines.account_id.id,
                            'partner_id': liquidity_lines[0].partner_id.id,
                        })
                else:
                    if len(liquidity_lines) == 1:
                        liquidity_amount = liquidity_lines.amount_currency
                        move_vals_to_write.update({
                            'currency_id': liquidity_lines.currency_id.id,
                            'partner_id': liquidity_lines.partner_id.id,
                        })
                        payment_vals_to_write.update({
                            'amount': abs(liquidity_amount),
                            'partner_type': partner_type,
                            'currency_id': liquidity_lines.currency_id.id,
                            'destination_account_id': counterpart_lines.account_id.id,
                            'partner_id': liquidity_lines.partner_id.id,
                        })
                    elif len(liquidity_lines) > 1:
                        liquidity_amount = 0
                        for liq in liquidity_lines:
                            liquidity_amount += liq.amount_currency
                        move_vals_to_write.update({
                            'currency_id': liquidity_lines[0].currency_id.id,
                            'partner_id': liquidity_lines[0].partner_id.id,
                        })
                        payment_vals_to_write.update({
                            'amount': abs(liquidity_amount),
                            'partner_type': partner_type,
                            'currency_id': liquidity_lines[0].currency_id.id,
                            'destination_account_id': counterpart_lines.account_id.id,
                            'partner_id': liquidity_lines[0].partner_id.id,
                        })
                if liquidity_amount > 0.0:
                    payment_vals_to_write.update({'payment_type': 'inbound'})
                elif liquidity_amount < 0.0:
                    payment_vals_to_write.update({'payment_type': 'outbound'})

            move.write(move._cleanup_write_orm_values(move, move_vals_to_write))
            pay.write(move._cleanup_write_orm_values(pay, payment_vals_to_write))

    def _synchronize_to_moves(self, changed_fields):
        ''' Update the account.move regarding the modified account.payment.
        :param changed_fields: A list containing all modified fields on account.payment.
        '''
        if self._context.get('skip_account_move_synchronization'):
            return

        if not any(field_name in changed_fields for field_name in (
            'date', 'amount', 'payment_type', 'partner_type', 'payment_reference', 'is_internal_transfer',
            'currency_id', 'partner_id', 'destination_account_id', 'partner_bank_id',
        )):
            return

        #DELET ITF - COMMISSION
        self.env['account.move.line'].search([('move_id','=',self.move_id.id),('itf_or_commission','=',True)]).unlink()

        for pay in self.with_context(skip_account_move_synchronization=True):
            liquidity_lines, counterpart_lines, writeoff_lines = pay._seek_for_lines()

            # Make sure to preserve the write-off amount.
            # This allows to create a new payment with custom 'line_ids'.

            if writeoff_lines:
                writeoff_amount = sum(writeoff_lines.mapped('amount_currency'))
                counterpart_amount = counterpart_lines['amount_currency']
                if writeoff_amount > 0.0 and counterpart_amount > 0.0:
                    sign = -1
                else:
                    sign = 1

                write_off_line_vals = {
                    'name': writeoff_lines[0].name,
                    'amount': writeoff_amount * sign,
                    'account_id': writeoff_lines[0].account_id.id,
                }
            else:
                write_off_line_vals = {}

            line_vals_list = pay._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals)

            line_ids_commands = [
                (1, liquidity_lines.id, line_vals_list[0]),
                (1, counterpart_lines.id, line_vals_list[1]),
            ]

            for line in writeoff_lines:
                line_ids_commands.append((2, line.id))

            if writeoff_lines:
                line_ids_commands.append((0, 0, line_vals_list[2]))

            #ITF OR COMMISSION
            for line_itf_comm in line_vals_list:
                if line_itf_comm['itf_or_commission'] == True:
                    line_ids_commands.append((0, 0, line_itf_comm))

            # Update the existing journal items.
            # If dealing with multiple write-off lines, they are dropped and a new one is generated.

            pay.move_id.write({
                'partner_id': pay.partner_id.id,
                'currency_id': pay.currency_id.id,
                'partner_bank_id': pay.partner_bank_id.id,
                'line_ids': line_ids_commands,
            })