# -*- coding: utf-8 -*-
# @see <a href="http://en.wikipedia.org/wiki/Verhoeff_algorithm">More Info</a>
# @see <a href="http://en.wikipedia.org/wiki/Dihedral_group">Dihedral Group</a>
# @see <a href="http://mathworld.wolfram.com/DihedralGroupD5.html">Dihedral Group Order 10</a>
# @author Hermann Himmelbauer

verhoeff_table_d = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
    (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
    (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
    (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
    (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
    (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
    (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
    (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
    (9, 8, 7, 6, 5, 4, 3, 2, 1, 0))
verhoeff_table_p = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
    (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
    (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
    (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
    (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
    (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
    (7, 0, 4, 6, 9, 1, 3, 2, 5, 8))
verhoeff_table_inv = (0, 4, 3, 2, 1, 5, 6, 7, 8, 9)


def calcsum(number):
    """For a given number returns a Verhoeff checksum digit"""
    c = 0
    for i, item in enumerate(reversed(str(number))):
        c = verhoeff_table_d[c][verhoeff_table_p[(i + 1) % 8][int(item)]]
    return verhoeff_table_inv[c]


def checksum(number):
    """For a given number generates a Verhoeff digit and
    returns number + digit"""
    c = 0
    for i, item in enumerate(reversed(str(number))):
        c = verhoeff_table_d[c][verhoeff_table_p[i % 8][int(item)]]
    return c


def generateVerhoeff(number):
    """For a given number returns number + Verhoeff checksum digit"""
    return "%s%s" % (number, calcsum(number))


def validateVerhoeff(number):
    """Validate Verhoeff checksummed number (checksum is last digit)"""
    return checksum(number) == 0
