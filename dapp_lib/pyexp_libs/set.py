# pyexp_libs/set.py

from ..pyexp import *

_module = {}

@pyexp_libs(set,[ 'clear', 'copy', 'difference', 'intersection',
  'discard', 'pop', 'remove' ])
def _new_dict(arg):  # _new_* means class declare
  ret = dict(arg)
  assert len(ret) <= PYEXP_LIST_MAX
  return ret

@pyexp_libs(set)
def have(self, item):
  return (item in self)

@pyexp_libs(set)
def add(self, sub):
  self.add(sub)
  return None

@pyexp_libs(set)
def union(self, value):
  ret = self.union(value)
  assert len(ret) <= PYEXP_LIST_MAX
  return None

@pyexp_libs(set)
def update(self, value):
  self.update(value)
  assert len(self) <= PYEXP_LIST_MAX
  return None
