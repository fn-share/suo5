# pyexp_libs/list.py

from ..pyexp import *

_module = {}

@pyexp_libs(list,[ 'count', 'clear', 'copy', 'pop', 'remove', 'reverse', 'sort' ])
def _new_list(arg):  # _new_* means class declare
  ret = list(arg)
  assert len(ret) <= PYEXP_LIST_MAX
  return ret

@pyexp_libs(list)
def have(self, item):
  return (item in self)

@pyexp_libs(list)
def get(self, sub):
  return self[sub]

@pyexp_libs(list)
def set(self, sub, item):
  self[sub] = item
  assert len(self) <= PYEXP_LIST_MAX
  return item

@pyexp_libs(list)
def slice(self, start=0, end=None, step=None):
  return self[start:end:step]

@pyexp_libs(list)
def setslice(self, start=0, end=None, value=None):
  ret = value or []
  self[start:end] = ret
  assert len(self) <= PYEXP_LIST_MAX
  return ret

@pyexp_libs(list)
def find(self, arg):
  try:
    return self.index(arg)
  except ValueError:
    return -1

@pyexp_libs(list)
def append(self, arg):
  self.append(arg)
  assert len(self) <= PYEXP_LIST_MAX
  return None

@pyexp_libs(list)
def extend(self, arg):
  self.extend(arg)
  assert len(self) <= PYEXP_LIST_MAX
  return None

@pyexp_libs(list)
def insert(self, sub, item):
  self.insert(sub,item)
  assert len(self) <= PYEXP_LIST_MAX
  return None
