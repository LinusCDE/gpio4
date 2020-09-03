#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Wed May 16 18:14:02 2018

@author: hank
@page:   https://github.com/hankso
"""

import re

class _sunxi():
    def __getitem__(self, pin):
        rst = re.findall(r"P([A-Z])(\d+)", str(pin))
        if not rst:
            raise KeyError('pin name {} not supported!'.format(pin))
        return 32*(ord(rst[0][0])-65) + int(rst[0][1])

class _bbb():
    def __init__(self):
        self._BBB_GPIO_MAP = {
            # All pins should be correct. However I might have mistyped one (copied over by hand from a sheet as png).
            'P8_03':  38,   'P8_04':  39,   'P8_05':  34,   'P8_06':  35,   'P8_07':  66,   'P8_08':  67,   'P8_09':  69,   'P8_10':  68,
            'P8_11':  45,   'P8_12':  44,   'P8_13':  23,   'P8_14':  26,   'P8_15':  47,   'P8_16':  46,   'P8_17':  27,   'P8_18':  65,
            'P8_19':  22,   'P8_20':  63,   'P8_21':  62,   'P8_22':  37,   'P8_23':  36,   'P8_24':  33,   'P8_25':  32,   'P8_26':  61,
            'P8_27':  86,   'P8_28':  88,   'P8_29':  87,   'P8_30':  89,   'P8_31':  10,   'P8_32':  11,   'P8_33':   9,   'P8_34':  81,
            'P8_35':   8,   'P8_36':  80,   'P8_37':  78,   'P8_38':  79,   'P8_39':  76,   'P8_40':  77,   'P8_41':  74,   'P8_42':  75,
            'P8_43':  72,   'P8_44':  73,   'P8_45':  70,   'P8_46':  71,

            'P9_11':  30,   'P9_12':  60,   'P9_13':  31,   'P9_14':  50,   'P9_15':  48,   'P9_16':  51,   'P9_17':   5,   'P9_18':   4,
            'P9_19':  13,   'P9_20':  12,   'P9_21':   3,   'P9_22':   2,   'P9_23':  49,   'P9_24':  15,   'P9_25':  117,   'P9_26':  14,
            'P9_27': 115,   'P9_28': 113,   'P9_29': 111,   'P9_30': 112,   'P9_31': 110,
            'P9_41':  20,   'P9_41A': 20,   'P9_41B':116,   'P9_42':   7,   'P9_42A':  7,   'P9_42B':114
        }
    def __getitem__(self, pin):
        # Accept formats for P8_08 wold be: e.g. p8_08, P8_08, p8.08, P8.08, p8.8, P8.8, p8_8 or P8_8
        rst = re.findall(r"^[Pp]([8,9])[._](\d+[A,B]?)$", str(pin))
        if not rst:
            raise KeyError('pin name {} not supported!'.format(pin))
        header_num, pin_name = rst[0]
        suffix = pin_name[-1] if pin_name.endswith('A') or pin_name.endswith('B') else ''
        pin_name = '%.2d%s' % (int(pin_name[:len(pin_name) - len(suffix)]), suffix)
        return self._BBB_GPIO_MAP['P%s_%s' % (header_num, pin_name)]


RISING       = 'rising'
FALLING      = 'falling'
CHANGE       = 'change'
BOTH         = 'both'
HIGH         = 1
LOW          = 0
INPUT        = 'in'
OUTPUT       = 'out'
INPUT_PULLUP = 'pullup'
INPUT_PULLDN = 'pulldn'
MSBFIRST     = 1
LSBFIRST     = 2
true         = True
false        = False
FOREVER      = 1e5
FOREVER_ms   = 1e5 * 1000

BOARD_SUNXI = _sunxi()
BOARD_NANO_PI = {}
BOARD_ORANGE_PI_PC = {}
BCM = {}
BOARD_BBB = _bbb()

__all__ = ['RISING', 'FALLING', 'CHANGE', 'HIGH', 'LOW',
           'OUTPUT', 'INPUT', 'INPUT_PULLUP', 'INPUT_PULLDN',
           'MSBFIRST', 'LSBFIRST', 'true', 'false', 'FOREVER', 'FOREVER_ms',
           'BOARD_SUNXI', 'BOARD_NANO_PI', 'BOARD_ORANGE_PI_PC', 'BCM']
