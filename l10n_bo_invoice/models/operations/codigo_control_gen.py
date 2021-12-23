# -*- coding: utf-8 -*-
from .Verhoeff import generateVerhoeff
from .RC4 import KSA, PRGA, RC4
import re
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import math


def base64_convert(valor):
    valores = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
               'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J',
               'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T',
               'U', 'V', 'W', 'X', 'Y', 'Z', 'a', 'b', 'c', 'd',
               'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n',
               'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x',
               'y', 'z', '+', '/']
    quotient = 1
    word = ""
    while quotient > 0:
        quotient = int(valor / 64)
        remainder = int(valor % 64)
        word = valores[remainder] + word
        valor = quotient
    return word


def get_codigo_control(n_autorizacion=0, n_factura=0, n_nitci=0, n_fecha='', monto_fac=0.0, llave=''):
    n_autorizacion = str(n_autorizacion)
    n_factura = str(n_factura)
    n_cinit = str(n_nitci)
    fecha_ini = n_fecha
    if fecha_ini.month > 9:
        mes = str(fecha_ini.month)
    else:
        mes = '0' + str(fecha_ini.month)

    if fecha_ini.day > 9:
        dia = str(fecha_ini.day)
    else:
        dia = '0' + str(fecha_ini.day)

    fecha = str(fecha_ini.year) + str(mes) + str(dia)
    monto = str(round(monto_fac, 0))
    monto = monto[:-2]
    llave = str(llave)

    # Nro de factura
    v_n_factura = generateVerhoeff(n_factura)
    v_n_factura = generateVerhoeff(v_n_factura)

    # Nit o ci
    v_n_cinit = generateVerhoeff(n_cinit)
    v_n_cinit = generateVerhoeff(v_n_cinit)

    # fecha
    v_fecha = generateVerhoeff(fecha)
    v_fecha = generateVerhoeff(v_fecha)

    # Monto
    v_monto = generateVerhoeff(monto)
    v_monto = generateVerhoeff(v_monto)

    total = int(v_n_factura) + int(v_n_cinit) + int(v_fecha) + int(v_monto)
    total_cinco = str(total)
    for x in range(0, 5):
        total_cinco = generateVerhoeff(total_cinco)

    valor_cinco = total_cinco[-5:]

    llave_dos = llave
    for i, c in enumerate(valor_cinco):
        cadena_uno = llave_dos[:int(c) + 1]
        llave_dos = llave_dos[(int(c) + 1):]
        if i == 0:
            n_autorizacion = n_autorizacion + cadena_uno
        if i == 1:
            v_n_factura = v_n_factura + cadena_uno
        if i == 2:
            v_n_cinit = v_n_cinit + cadena_uno
        if i == 3:
            v_fecha = v_fecha + cadena_uno
        if i == 4:
            v_monto = v_monto + cadena_uno

    cadena_total = n_autorizacion + v_n_factura + v_n_cinit + v_fecha + v_monto

    def convert_key(s):
        return [ord(c) for c in s]

    key = llave + valor_cinco
    key = convert_key(key)
    keystream = RC4(key)

    valor_rc4 = ''
    for c in cadena_total:
        valor_rc4 = valor_rc4 + ("%02X" % (ord(c) ^ keystream.__next__()))

    total_ascii = sum(bytearray(valor_rc4, 'utf8'))

    for n in range(1, 6):
        str_total1 = ''
        for i, c in enumerate(valor_rc4, start=1):
            if i == n:
                n = n + 5
                str_total1 = str_total1 + c
    total_base = 0
    valor_eof = []
    for line in valor_cinco:
        valor_eof.append(line)
    indice = 1
    for n in range(1, 6):
        str_total1 = ''
        for i, c in enumerate(valor_rc4, start=1):
            if i == n:
                n = n + 5
                str_total1 = str_total1 + c
        total1 = sum(bytearray(str_total1, 'utf8'))
        valor_sumar = math.trunc(((int(total_ascii) * total1) / (int(valor_eof[indice - 1]) + 1)))
        total_base = total_base + valor_sumar
        indice = indice + 1

    valor = base64_convert(total_base)

    key = llave + valor_cinco
    key = convert_key(key)
    keystream = RC4(key)

    valor_cc = ''
    for c in valor:
        valor_cc = valor_cc + ("%02X" % (ord(c) ^ keystream.__next__()))

    valor_re = re.findall('..', valor_cc)
    codigo_control = ''
    for val_re in valor_re:
        codigo_control = codigo_control + val_re + '-'
    # Quitamos el guion que se añade de mas
    cc = codigo_control[:-1]
    return cc
