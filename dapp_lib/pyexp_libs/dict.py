# pyexp_libs/dict.py

from ..pyexp import *

_module = {}

@pyexp_libs(dict,[ 'clear', 'copy', 'keys', 'items', 'pop', 'values' ])
def _new_dict(arg):  # _new_* means class declare
  ret = dict(arg)
  assert len(ret) <= PYEXP_LIST_MAX
  return ret

@pyexp_libs(dict)
def have(self, item):
  return (item in self)

@pyexp_libs(dict)
def get(self, sub):
  return self[sub]

@pyexp_libs(dict)
def set(self, sub, item):
  self[sub] = item
  assert len(self) <= PYEXP_LIST_MAX
  return item

@pyexp_libs(dict)
def update(self, value):
  self.update(value)
  assert len(self) <= PYEXP_LIST_MAX
  return None
