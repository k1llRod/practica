from odoo import api, fields, models, _, registry
from odoo.exceptions import UserError, ValidationError
from .operations.codigo_control_gen import get_codigo_control


class DosingControl(models.Model):
    _name = 'dosing.control'
    _description = 'Control de Dosificación por Actividad Económica'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = "date_end"

    active = fields.Boolean('Active', default=True)
    name = fields.Char(string='Nombre del Certificado')
    date_init = fields.Date(string='Válido desde', required=True)
    date_end = fields.Date(string='Fecha límite', required=True)
    n_autorizacion = fields.Char(string="Nro. Autorización", required=True,
                                 default=0)
    sucursal_id = fields.Many2one('stock.warehouse', string='Sucursal',
                                  required=False)
    type = fields.Selection([
        ('manual', 'Manual'),
        ('automatica', 'Computarizada')
    ], required=True, default='automatica', string='Modalidad de Facturación')
    type_inv = fields.Selection([
        ('invoice', 'Factura'),
        ('notes', 'Notas de Crédito/Débito')
    ], required=True, default='invoice', string='Tipo de Documento Fiscal',
        help='Seleccionar las opcion de la Dosificación generada')
    n_factura_inicial = fields.Integer(string='Nro. Inicial',
                                       default=1)
    n_factura_actual = fields.Integer(string='Nro. Actual',
                                      default=1, readonly=True)
    n_factura_limite = fields.Integer(string='Nro. Limite',
                                      default=1000)
    company_id = fields.Many2one('res.company', string="Compañía",
                                 default=lambda self: self.env.user.company_id)
    llave = fields.Char(string="Llave", required=True)
    actividad = fields.Many2one("economic.activity",
                                string="Actividad Económica")
    leyenda = fields.Many2one("legend.control", string="Leyenda Asignada")
    tiempo_alerta = fields.Integer(string='Tiempo Aviso',
                                   help='Tiempo de aviso para alertar el vencimiento de la dosificación registrada')

    # def test(self):
    #     vartest = self.env.ref('sale.sale_order_' + str(10))
    #     print(vartest.amount_total)

    @api.model
    def run_alerta(self, use_new_cursor=False, company_id=False):
        try:
            # if use_new_cursor:
            cr = registry(self._cr.dbname).cursor()
            self = self.with_env(self.env(cr=cr))

            group = self.env.ref('account.group_account_manager')
            usuario = group.users
            sql_query = """select *
                                    from (
                                           select
                                             *,
                                             (fecha_actual + (foo.tiempo_alerta :: text || ' day') :: INTERVAL) as fecha_alerta
                                           from (select
                                                   t0.id,
                                                   t0.name,
                                                   t0.date_end,
                                                   coalesce(t0.tiempo_alerta, 0)        as tiempo,
                                                   (now() - interval '4 hours') :: DATE as fecha_actual,
                                                   t0.tiempo_alerta
                                                 from dosing_control t0
                                                 where t0.active = true
                                                 ) as foo
                                         ) as foo2
                                    where foo2.fecha_alerta > foo2.date_end
                                                                            """
            self.env.cr.execute(sql_query)
            val = 0
            ids_dosing = []
            message = "<div style='font-size:14px;'><b>Alerta Series dosificación</b></div>"
            for line in self.env.cr.dictfetchall():
                message = message + """
                    <div>La dosificación: <b>""" + str(line.get('name')) + """ 
                    </b> caducará en fecha: <b>""" + str(line.get('date_end')) + """ 
                    </b></div>
                    <div><a style='background-color: #875A7B;
                        padding: 8px 16px 8px 16px;
                        text-decoration: none;
                        color: #fff;
                        border-radius: 5px;
                        display: inline-block;
                        margin-top:4px;' 
                        href=# data-oe-model=dosing.control data-oe-id=""" + str(line.get('id')) + """
                        >Ver</a>
                    </div>"""
                val = 1
                ids_dosing.append(line.get('id'))

            if val > 0:
                notification_ids = []
                for d in self.env['dosing.control'].browse(ids_dosing):
                    for us in usuario:
                        notification_ids.append((0, 0, {
                            'res_partner_id': us.partner_id.id,
                            'notification_type': 'inbox'}))

                    new_msg = d.message_post(body=message,
                                             message_type='comment',
                                             subtype_id=self.env.ref(
                                                 'mail.mt_comment').id,
                                             notification_ids=notification_ids)
                    new_msg.sudo().write(
                        {'notification_ids': notification_ids})
                cr.commit()
        finally:
            if use_new_cursor:
                try:
                    self._cr.close()
                except Exception:
                    pass

        return True

    #   Verificar que el número inicial de la factura sea mayor al número límite
    @api.onchange('n_factura_inicial', 'n_factura_limite')
    def onchange_factura_inicial_limite(self):
        if (self.n_factura_limite <= self.n_factura_inicial):
            raise ValidationError(_('El número de la factura Inicial no puede ser mayor al Límite'))

    @api.model
    def get_codigo_control(self, n_factura, nit_ci, fecha, monto):
        for line in self:
            codigo_control = get_codigo_control(line.n_autorizacion, n_factura,
                                                nit_ci, fecha, monto,
                                                line.llave)
        return codigo_control

    @api.model
    def plus_factura(self):
        for dosi in self:
            dosi.n_factura_actual += 1
