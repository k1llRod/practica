# -*- coding: utf-8 -*-
{
    'name': "Descuentos por linea de factura",

    'summary': """
        Descuentos por linea de factura""",

    'description': """
        Generacion de desccuentos por lineas de factura
    """,

    'author': "versatil srl",
    'website': "http://www.versatil.com.bo",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Account',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['l10n_bo_invoice','sale'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'report/report_sale_discount.xml',
        'views/account_move_view.xml',
        'views/sale_order.xml',
        'wizard/wizard_sale_discount.xml',
    ],
}