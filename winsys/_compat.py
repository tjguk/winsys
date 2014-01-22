# -*- coding: utf-8 -*-
try:
    unicode
except NameError:
    unicode = str

try:
    reduce
except NameError:
    from functools import reduce

try:
    basestring
except NameError:
    basestring = str
