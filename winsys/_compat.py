# -*- coding: utf-8 -*-
"""Assist 2->3 porting by giving assigning defunct to sane objects.

NB This module *MUST NOT* import any winsys modules
"""
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

try:
    long
except NameError:
    long = int
