# -*- coding: utf-8 -*-
{
    'name': "Cálculo de Exentos Localización Boliviana",

    'summary': """
        Agrega la funcionalidad de cálculo de exentos en facturas de proveedor""",

    'description': """
        Cálculo de exentos en facturas proveedor
    """,

    'author': "Versatil SRL - Carlos López",
    'website': "https://versatil.com.bo",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Account',
    'version': '14.1',

    # any module necessary for this one to work correctly
    'depends': ['base','account','l10n_bo_invoice'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/inherit_account_move_view.xml',
    ],
}
