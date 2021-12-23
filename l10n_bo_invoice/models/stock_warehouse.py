from odoo import api, fields, models


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'


    dosificacion = fields.Many2one(comodel_name='dosing.control',
                                   string='Certificado de Activación (Facturas)',
                                   domain=[
                                       ('sucursal_id','=',False),
                                       ('type_inv', '=', 'invoice')
                                   ])
    dosificacion_dc = fields.Many2one(comodel_name='dosing.control',
                                      string='Certificado Activación(Notas Crédito/Débito)',
                                      domain=[
                                          ('sucursal_id','=',False),
                                          ('type_inv', '=', 'notes')
                                      ])
    casa_matriz = fields.Boolean(string='Casa Matríz', default=False)

    def write(self, vals):
        if vals.get('dosificacion', False):
            dosificacion = self.env['dosing.control'].browse(
                vals['dosificacion'])
            for warehouse in self:
                dosificacion.sucursal_id = warehouse.id
        if vals.get('dosificacion_dc', False):
            dosificacion = self.env['dosing.control'].browse(
                vals['dosificacion_dc'])
            for warehouse in self:
                dosificacion.sucursal_id = warehouse.id
        return super(StockWarehouse, self).write(vals)