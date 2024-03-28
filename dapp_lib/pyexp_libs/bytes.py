# pyexp_libs/bytes.py

from ..pyexp import *

_module = {}

@pyexp_libs(bytes,[ 'count', 'startswith', 'endswith', 'find', 'rfind',
  'isalnum', 'isalpha', 'isascii', 'isdigit', 'isspace',
  'lower', 'upper', 'strip', 'lstrip', 'rstrip',
  'split', 'rsplit', 'splitlines' ])
def _new_bytes(arg):  # _new_* means class declare
  ret = bytes(arg)
  assert len(ret) <= PYEXP_STR_MAX
  return ret

@pyexp_libs(bytes)
def have(self, item):
  return (item in self)

@pyexp_libs(bytes)
def get(self, sub):
  return self[sub]

@pyexp_libs(bytes)
def slice(self, start=0, end=None, step=None):
  return self[start:end:step]

@pyexp_libs(bytes)
def decode(self):
  return self.decode('utf-8')

@pyexp_libs(bytes)
def join(self, arg):
  ret = self.join(arg)
  assert len(ret) <= PYEXP_STR_MAX
  return ret

@pyexp_libs(bytes)
def center(self, n, fill=b' '):
  ret = self.center(n,fill)
  assert len(ret) <= PYEXP_STR_MAX
  return ret

@pyexp_libs(bytes)
def ljust(self, n, fill=b' '):
  ret = self.ljust(n,fill)
  assert len(ret) <= PYEXP_STR_MAX
  return ret

@pyexp_libs(bytes)
def rjust(self, n, fill=b' '):
  ret = self.rjust(n,fill)
  assert len(ret) <= PYEXP_STR_MAX
  return ret

@pyexp_libs(bytes)
def replace(self, sub, count=-1):
  ret = self.replace(sub,count)
  assert len(ret) <= PYEXP_STR_MAX
  return ret

@pyexp_libs(bytes)
def zfill(self, n):
  ret = self.zfill(n)
  assert len(ret) <= PYEXP_STR_MAX
  return ret
