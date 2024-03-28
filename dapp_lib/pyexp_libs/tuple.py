# pyexp_libs/tuple.py

from ..pyexp import *

_module = {}

@pyexp_libs(tuple,[ 'count' ])
def _new_tuple(arg):  # _new_* means class declare
  ret = tuple(arg)
  assert len(ret) <= PYEXP_LIST_MAX
  return ret

@pyexp_libs(tuple)
def have(self, item):
  return (item in self)

@pyexp_libs(tuple)
def get(self, sub):
  return self[sub]

@pyexp_libs(tuple)
def slice(self, start=0, end=None, step=None):
  return self[start:end:step]

@pyexp_libs(tuple)
def find(self, arg):
  try:
    return self.index(arg)
  except ValueError:
    return -1
