# pyexp_libs/str.py

from ..pyexp import *

_module = {}

@pyexp_libs(str,[ 'count', 'startswith', 'endswith', 'find', 'rfind',
  'isalnum', 'isalpha', 'isascii', 'isdigit', 'isspace',
  'lower', 'upper', 'strip', 'lstrip', 'rstrip',
  'split', 'rsplit', 'splitlines' ])
def _new_str(arg):  # _new_* means class declare
  ret = str(arg)
  assert len(ret) <= PYEXP_STR_MAX
  return ret

@pyexp_libs(str)
def have(self, item):
  return (item in self)

@pyexp_libs(str)
def get(self, sub):
  return self[sub]

@pyexp_libs(str)
def slice(self, start=0, end=None, step=None):
  return self[start:end:step]

@pyexp_libs(str)
def encode(self):
  return self.encode('utf-8')

@pyexp_libs(str)
def join(self, arg):
  ret = self.join(arg)
  assert len(ret) <= PYEXP_STR_MAX
  return ret

@pyexp_libs(str)
def center(self, n, fill=' '):
  ret = self.center(n,fill)
  assert len(ret) <= PYEXP_STR_MAX
  return ret

@pyexp_libs(str)
def ljust(self, n, fill=' '):
  ret = self.ljust(n,fill)
  assert len(ret) <= PYEXP_STR_MAX
  return ret

@pyexp_libs(str)
def rjust(self, n, fill=' '):
  ret = self.rjust(n,fill)
  assert len(ret) <= PYEXP_STR_MAX
  return ret

@pyexp_libs(str)
def replace(self, sub, count=-1):
  ret = self.replace(sub,count)
  assert len(ret) <= PYEXP_STR_MAX
  return ret

@pyexp_libs(str)
def zfill(self, n):
  ret = self.zfill(n)
  assert len(ret) <= PYEXP_STR_MAX
  return ret
