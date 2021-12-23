# -*- coding: utf-8 -*-
{
    'name': "l10n_bo_invoice",

    'summary': """
        Bolivia - Módulo localización para Bolivia""",

    'description': """
        Módulo localización para Bolivia
    """,

    'author': "Carlos N. López Fernández","Franklin Justiniano"
    'website': "https://versatil.odoo.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'SIN',
    'version': '14.1',

    # any module necessary for this one to work correctly
    'depends': ['base',
                'account',
                'stock',
                'contacts',
                'sale',
                'purchase'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/templates.xml',
        'views/valid_code_control.xml',
        'views/legends.xml',
        'views/economic_activity.xml',
        'views/dosing_control.xml',
        'views/res_partner_view.xml',
        'views/account_move_view.xml',
        'views/stock_warehouse.xml',
        'views/company_view.xml',
        'views/report_invoice.xml',
        'views/sale_order_view.xml',
        'views/product_view.xml',
        'views/account_payment_view.xml',
        'views/account_tax_view.xml',
        'views/purchase_view.xml',
        'views/res_config_settings_view.xml',
        'views/res_user.xml',
        'data/cron_view.xml',
        'data/default_legends_view.xml',
        'wizard/account_move_reversal_view.xml',
        'views/assets.xml',
        'views/account_journal_view.xml',
    ],
    "qweb":[
        'static/src/xml/field_codigo_control.xml',
    ]
}
