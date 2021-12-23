from odoo import api, fields, models
from odoo.osv.expression import get_unaccent_wrapper
import re


class ModResPartner(models.Model):
    _inherit = 'res.partner'

    razon_social = fields.Char(string='Razón Social', size=100, required=True, default='S/N')
    nit_ci = fields.Char(string='NIT/CI',size=12,required=True, index=True, default='0')
    expedido = fields.Selection([
        ('La Paz', 'LP'),
        ('Oruro', 'OR'),
        ('Cochabamba', 'CB'),
        ('Santa Cruz', 'SZ'),
        ('Beni', 'BN'),
        ('Pando', 'PN'),
        ('Chuquisaca', 'CH'),
        ('Tarija', 'TJ'),
        ('Potosi', 'PT'),
        ('Extranjero', 'EX')
    ],string='Expedido en')
    extension = fields.Char('Extensión', help="Usar sólo en CARNETS DE IDENTIDAD que tengan extensión.")
    vat = fields.Char(string="Tax ID", readonly=False, compute="inst_vat")

    @api.onchange('name')
    def name_onchange(self):
        for partner in self:
            self.razon_social = partner.name

    @api.onchange('nit_ci')
    def inst_vat(self):
        for rec in self:
            rec.vat = rec.nit_ci
    # def nit_ci_onchange(self):
    #     for partner in self:
    #         partner.vat = self.nit_ci


    def _name_search(self, name, args=None, operator='ilike', limit=100,
                     name_get_uid=None):

        self = self.with_user(name_get_uid or self.env.uid)
        # as the implementation is in SQL, we force the recompute of fields if necessary
        self.recompute(['display_name'])
        self.flush()
        if args is None:
            args = []
        order_by_rank = self.env.context.get('res_partner_search_mode')
        if (name or order_by_rank) and operator in (
        '=', 'ilike', '=ilike', 'like', '=like'):
            self.check_access_rights('read')
            where_query = self._where_calc(args)
            self._apply_ir_rules(where_query, 'read')
            from_clause, where_clause, where_clause_params = where_query.get_sql()
            from_str = from_clause if from_clause else 'res_partner'
            where_str = where_clause and (
                        " WHERE %s AND " % where_clause) or ' WHERE '

            # search on the name of the contacts and of its company
            search_name = name
            if operator in ('ilike', 'like'):
                search_name = '%%%s%%' % name
            if operator in ('=ilike', '=like'):
                operator = operator[1:]

            unaccent = get_unaccent_wrapper(self.env.cr)

            fields = self._get_name_search_order_by_fields()

            query = """SELECT res_partner.id
                         FROM {from_str}
                      {where} ({email} {operator} {percent}
                           OR {display_name} {operator} {percent}
                           OR {reference} {operator} {percent}
                           OR {vat} {operator} {percent}
                           OR {nit_ci} {operator} {percent})                           
                           -- don't panic, trust postgres bitmap
                     ORDER BY {fields} {display_name} {operator} {percent} desc,
                              {display_name}
                    """.format(from_str=from_str,
                               fields=fields,
                               where=where_str,
                               operator=operator,
                               email=unaccent('res_partner.email'),
                               display_name=unaccent(
                                   'res_partner.display_name'),
                               reference=unaccent('res_partner.ref'),
                               percent=unaccent('%s'),
                               vat=unaccent('res_partner.vat'),
                               nit_ci=unaccent('nit_ci'),)

            where_clause_params += [
                                       search_name] * 3  # for email / display_name, reference
            where_clause_params += [
                re.sub('[^a-zA-Z0-9]+', '', search_name) or None]  # for vat
            where_clause_params += [search_name]  # for order by
            where_clause_params += [search_name]  # for nit_ci
            if limit:
                query += ' limit %s'
                where_clause_params.append(limit)
            self.env.cr.execute(query, where_clause_params)
            return [row[0] for row in self.env.cr.fetchall()]

        return super(ModResPartner, self)._name_search(name, args, operator=operator,
                                                 limit=limit,
                                                 name_get_uid=name_get_uid)

    # def create(self, vals):
    #     result = super(ModResPartner, self).create(vals)
    #     result.vat = result.nit_ci
    #     return result



