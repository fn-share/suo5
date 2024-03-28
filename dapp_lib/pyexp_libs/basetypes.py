# pyexp_libs/basetypes.py

from ..pyexp import *

_module = {}

_module['null'] = None   # for compatible loading json

#---- regist global functions: int float bool len log

@pyexp_libs(None, 'int')
def _int(arg):
  return int(arg)

@pyexp_libs(None, 'float')
def _float(arg):
  return float(arg)

@pyexp_libs(None, 'bool')
def _bool(arg):
  return bool(arg)

@pyexp_libs(None, 'len')
def _len(arg):
  return len(arg)

@pyexp_libs(None, 'log')
def _log(*args):
  return print(*args)

#---- load class: str bytes

from . import str as _str
from . import bytes as _bytes

_module.update(_str._module)
_module.update(_bytes._module)

#---- load class: tuple list dict set

from . import tuple as _tuple
from . import list as _list
from . import dict as _dict
from . import set as _set

_module.update(_tuple._module)
_module.update(_list._module)
_module.update(_dict._module)
_module.update(_set._module)
