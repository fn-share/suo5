# formatter.py

__all__ = [ 'Nb','NB','Nh','NH','Ni','NI','Nq','NQ','Nf','Nd','VarInt','VarStr',
  'bytesOf', 'arrayOf', 'composeOf', 'Formatter', 'VarStrList', 'IpAddr', 'compose' ]

import struct
from binascii import unhexlify

_endianness = '>'

class Formatter(bytes):
  _struct_ = struct.Struct(_endianness)
  
  _len_  = 0  # _struct_.size  # wait overwrite
  _type_ = 'Formatter'         # wait overwrite
  
  def __new__(cls, data, *args, **kwargs):
    assert isinstance(data,bytes)
    return bytes.__new__(cls,data)
  
  @property
  def _type(self):
    return self.__class__._type_
  
  @property
  def _len(self):
    return self.__class__._len_
  
  @property
  def _(self):
    return self
  
  @classmethod
  def decode(cls, data, offset=0):
    return cls(data[offset:offset+cls._len_])
  
  @classmethod
  def encode(cls, value):
    return cls(cls._struct_.pack(value))
  
  def __repr__(self):
    return '<%s(len=%i,value=0x%s)>' % (self._type,len(self),self.hex())

class Nb(Formatter):
  _struct_ = struct.Struct(_endianness + 'b')  # default as signed byte
  
  _len_ = 1     # _struct_.size
  _type_ = 'Nb'
  
  def __init__(self, data, verify=False):
    self._cache = None
  
  @property
  def _(self):
    if self._cache is None:
      n = self.__class__._struct_.unpack(self)[0]
      self._cache = n
      return n
    else: return self._cache

class NB(Nb):
  _struct_ = struct.Struct(_endianness + 'B')
  _len_ = 1
  _type_ = 'NB'
class Nh(Nb):
  _struct_ = struct.Struct(_endianness + 'h')
  _len_ = 2
  _type_ = 'Nh'
class NH(Nb):
  _struct_ = struct.Struct(_endianness + 'H')
  _len_ = 2
  _type_ = 'NH'
class Ni(Nb):
  _struct_ = struct.Struct(_endianness + 'i')
  _len_ = 4
  _type_ = 'Ni'
class NI(Nb):
  _struct_ = struct.Struct(_endianness + 'I')
  _len_ = 4
  _type_ = 'NI'
class Nq(Nb):
  _struct_ = struct.Struct(_endianness + 'q')
  _len_ = 8
  _type_ = 'Nq'
class NQ(Nb):
  _struct_ = struct.Struct(_endianness + 'Q')
  _len_ = 8
  _type_ = 'NQ'
class Nf(Nb):
  _struct_ = struct.Struct(_endianness + 'f')
  _len_ = 4
  _type_ = 'Nf'
class Nd(Nb):
  _struct_ = struct.Struct(_endianness + 'd')
  _len_ = 8
  _type_ = 'Nd'

class _BytesN(Formatter):
  def __init__(self, data, verify=True):
    if verify:
      assert len(data) == self.__class__._len_, 'size of %s mismatch' % (self.__class__._type_,)
  
  @classmethod
  def encode(cls, msg):
    if isinstance(msg,str):
      msg = msg.encode('utf-8')[:cls._len_].ljust(cls._len_,b'\x00')
    assert len(msg) == cls._len_, 'size of %s mismatch' % (cls._type_,)
    return cls(msg,verify=False)
  
  @property
  def _len(self):
    return self.__class__._len_
  
  def __repr__(self):
    n = len(self)
    desc = (self[:8].hex() + '...') if n > 8 else self.hex()
    return '<%s(len=%i,value=0x%s)>' % (self._type,n,desc)

def bytesOf(n):
  assert n > 0 and n <= 65535
  
  class _ClassInfo:
    _len_ = n
    _type_ = 'S[%i]' % n    # hint: not B[n], obj._ is bytes, not [B,B...]
  
  class BytesN(_ClassInfo,_BytesN):
    pass
  
  return BytesN

def _numOfVInt(b1, value):
  if b1 == 0xfd:
    return struct.unpack(_endianness+'H', value[1:3])[0]
  elif b1 == 0xfe:
    return struct.unpack(_endianness+'I', value[1:5])[0]
  elif b1 == 0xff:
    return struct.unpack(_endianness+'Q', value[1:9])[0]
  else: return b1

def _bytesOfVInt(value):
  if value < 0xfd:
    return struct.pack(_endianness+'B',value)
  elif value <= 0xffff:
    return b'\xfd' + struct.pack(_endianness+'H',value)
  elif value <= 0xffffffff:
    return b'\xfe' + struct.pack(_endianness+'I',value)
  else: return b'\xff' + struct.pack(_endianness+'Q',value)

class VarInt(Formatter):
  _len_ = 0   # _len_ not used in VarInt
  _type_ = 'VarInt'
  
  def __init__(self, data, verify=True, cache=None):
    if verify:
      n = len(data)
      if n == 1:
        assert ord(data[:1]) < 0xfd, 'size of %s mismatch' % (self.__class__._type_,)
      elif n == 3:
        assert ord(data[:1]) == 0xfd , 'size of %s mismatch' % (self.__class__._type_,)
      elif n == 5:
        assert ord(data[:1]) == 0xfe, 'size of %s mismatch' % (self.__class__._type_,)
      else: assert n == 9 and ord(data[:1]) == 0xff, 'size of %s mismatch' % (self.__class__._type_,)
    self._cache = cache
  
  @property
  def _(self):
    if self._cache is None:
      self._cache = _numOfVInt(ord(self[:1]),self)
    return self._cache
  
  @classmethod
  def encode(cls, value):
    return cls(_bytesOfVInt(value),verify=False,cache=value)
  
  @classmethod
  def decode(cls, data, offset=0):
    n = ord(data[offset:offset+1])
    size = 1 if n <= 0xfc else (3 if n == 0xfd else (5 if n == 0xfe else 9))
    return cls(data[offset:offset+size],verify=False)

class VarStr(Formatter):
  _len_ = 0  # _len_ not used in variant type
  _type_ = 'VarStr'
  
  def __init__(self, data, verify=True):
    if verify:
      n = len(data); n2 = _numOfVInt(ord(data[:1]),data)
      if n <= 0xfd:          # max length: 0xfc + 1
        assert n == n2 + 1, 'size of %s mismatch' % (self.__class__._type_,)
      elif n <= 65538:       # max length: 0xffff + 3
        assert n == n2 + 3, 'size of %s mismatch' % (self.__class__._type_,)
      elif n <= 4294967300:  # max length: 0xffffffff + 5
        assert n == n2 + 5, 'size of %s mismatch' % (self.__class__._type_,)
      else: assert n == n2 + 9, 'size of %s mismatch' % (self.__class__._type_,)
      self._cache = n2
    else: self._cache = None
  
  @property
  def _len(self):
    if self._cache is None:
      self._cache = _numOfVInt(ord(self[:1]),self)
    return self._cache
  
  @property
  def _(self):  # as bytes, not [B,B, ...] # not using cache since _ maybe huge
    n = self._len
    if n < 0xfd:
      return self[1:1+n]
    elif n <= 0xffff:
      return self[3:3+n]
    elif n <= 0xffffffff:
      return self[5:5+n]
    else: return self[9:9+n]
  
  @classmethod
  def encode(cls, value):
    if isinstance(value,str):
      value = value.encode('utf-8')
    return cls(_bytesOfVInt(len(value)) + value,verify=False)
  
  @classmethod
  def decode(cls, data, offset=0):
    n = _numOfVInt(ord(data[offset:offset+1]),data[offset:offset+9])
    off = 1 if n <= 0xfc else (3 if n <= 0xffff else (5 if n <= 0xffffffff else 9))
    obj = cls(data[offset:offset+off+n],verify=False)
    obj._cache = n
    return obj
  
  def __repr__(self):
    return '<%s(len=%i)>' % (self._type,self._len)  # not show detail, maybe it is huge

class _VarCls(Formatter):  # variant array of class
  def __init__(self, data, verify=True, cache=None, off=0):
    if verify and cache is not None:
      assert _numOfVInt(ord(data[off:off+1]),data[off:off+9]) == len(cache), 'size of %s mismatch' % (self.__class__._type_,)
    self._cache = cache
    self._cache2 = None if cache is None else len(cache)
    self._off = off
  
  @property
  def _len(self):
    if self._cache2 is None:
      self._cache2 = _numOfVInt(ord(self[self._off:self._off+1]),self[self._off:self._off+9]) if self._cache is None else len(self._cache)
    return self._cache2
  
  @property
  def _(self):
    if self._cache is not None:
      return self._cache
    
    cls = self.__class__._membcls_
    n = self._len
    
    off = 1 if n <= 0xfc else (3 if n <= 0xffff else (5 if n <= 0xffffffff else 9))
    off += self._off
    
    b = []; off2 = 0
    for i in range(n):
      obj = cls.decode(self,off+off2)
      b.append(obj)
      off2 += len(obj)
    
    self._cache = b
    return b
  
  @classmethod
  def encode(cls2, b):
    cls = cls2._membcls_
    b2 = [item if isinstance(item,Formatter) else cls.encode(item) for item in b]
    return cls2(_bytesOfVInt(len(b2)) + b''.join(b2),verify=False,cache=b2)
  
  @classmethod
  def decode(cls2, data, offset=0):
    obj = cls2(data,verify=False,cache=None,off=offset)  # hold data in obj temporary
    b2 = obj._
    return cls2(_bytesOfVInt(len(b2))+b''.join(b2),verify=False,cache=b2,off=0)
  
  def __repr__(self):
    return '<%s(len=%i)>' % (self._type,self._len)  # not show detail

def _variantOf(cls):  # variant array of cls
  class _ClassInfo:
    _membcls_ = cls
    _len_ = 0
    _type_ = cls._type_ + '[0]'
  
  class VarCls(_ClassInfo,_VarCls):
    pass
  
  return VarCls

class _ArrayCls(Formatter):
  def __init__(self, data, verify=True, cache=None, off=0):
    if verify and cache:
      assert len(cache) == self.__class__._len_, 'size of %s mismatch' % (self.__class__._type_,)
    self._cache = cache
    self._off = off
  
  @property
  def _len(self):
    return self.__class__._len_
  
  @property
  def _(self):
    if self._cache is not None:
      return self._cache
    
    cls = self.__class__._membcls_
    b = []
    n = self._len; off = self._off; off2 = 0
    for i in range(n):
      obj = cls.decode(self,off+off2)
      b.append(obj)
      off2 += len(obj)
    
    self._cache = b
    return b
  
  @classmethod
  def encode(cls2, b):
    assert len(b) == cls2._len_, 'size of %s mismatch' % (cls2._type_,)
    
    cls = cls2._membcls_
    b2 = [item if isinstance(item,Formatter) else cls.encode(item) for item in b]
    return cls2(b''.join(b2),verify=False,cache=b2)
  
  @classmethod
  def decode(cls2, data, offset=0):
    obj = cls2(data,verify=False,cache=None,off=offset)  # hold data in obj temporary
    b2 = obj._
    return cls2(b''.join(b2),verify=False,cache=b2,off=0)
  
  def __repr__(self):
    return '<%s(len=%i)>' % (self._type,self._len)  # not show detail

def arrayOf(cls, arr_size):
  if not arr_size:    # arr_size = 0 means variant array
    return _variantOf(cls)
  
  class _ClassInfo:
    _membcls_ = cls
    _len_ = arr_size
    _type_ = cls._type_ + ('[%i]' % arr_size)
  
  class ArrayCls(_ClassInfo,_ArrayCls):
    pass
  
  return ArrayCls

VarStrList = arrayOf(VarStr,0)

_base_types = { 'Nb':True, 'NB':True, 'Nh':True, 'NH':True,
  'Ni':True, 'NI':True, 'Nq':True, 'NQ':True, 'Nf':True, 'Nd':True,
  'VarInt':True, 'VarStr':True }

class _EasyDict(dict):
  def __new__(cls, data, *args, **kwargs):
    return dict.__new__(cls,data)
  
  def __getattr__(self, attr):
    if attr[0] == '_':  # easy access grammar, dict._attr is same to dict.attr._
      v = self[attr[1:]]
      return v._ if v.__class__._type_ in _base_types else v
    else: return self[attr]
  
  def __setattr__(self, attr, value):
    raise SyntaxError('no setter')
  
  def __delattr__(self, key):
    raise SyntaxError('no setter')

class _ComposeCls(Formatter):
  def __init__(self, data, verify=True, cache=None, off=0):
    if verify and cache:
      assert len(cache) == self.__class__._len_, 'size of %s mismatch' % (self.__class__._type_,)
    self._cache = cache
    self._off = off
  
  @property
  def _len(self):
    return self.__class__._len_
  
  @property
  def _(self):
    if self._cache is not None:
      return self._cache
    
    d = {}
    off = self._off; off2 = 0
    for name,cls in self.__class__._membs_:
      obj = cls.decode(self,off+off2)
      d[name] = obj
      off2 += len(obj)
    
    self._cache = d = _EasyDict(d)
    return d
  
  @classmethod
  def encode(cls2, _=None, **kwargs):
    if _ is None:
      dIn = kwargs
    else:
      dIn = _
      assert isinstance(dIn,dict), 'encode compose expecting dict items'
    
    d = {}; counter = 0; ctx = b''
    for name,cls in cls2._membs_:
      v = dIn.get(name,None)
      if v is None: raise SyntaxError('%s requires attribute: %s' % (cls2._type_,name))
      
      obj = v if isinstance(v,Formatter) else cls.encode(v)
      d[name] = obj
      ctx += obj
      counter += 1
    assert counter == cls2._len_, 'size of %s mismatch' % (cls2._type_,)
    
    return cls2(ctx,verify=False,cache=_EasyDict(d))
  
  @classmethod
  def decode(cls2, data, offset=0):
    obj = cls2(data,verify=False,cache=None,off=offset)  # hold data in obj temporary
    ctx = obj._; b = b''
    for item in cls2._membs_:
      b += ctx[item[0]]
    return cls2(b,verify=False,cache=ctx,off=0)
  
  def __repr__(self):
    return '<%s(memb=%i)>' % (self._type,self._len)  # not show detail

def composeOf(memb_def, cls_name='class'):
  assert isinstance(memb_def,(tuple,list)) and memb_def
  
  class _ClassInfo:
    _membs_ = memb_def
    _len_ = len(memb_def)
    _type_ = cls_name
  
  class ComposeCls(_ClassInfo,_ComposeCls):
    pass
  
  return ComposeCls


#----

import types

_ZERO_STR10  = b'\x00' * 10
_IP_HEAD_STR = _ZERO_STR10 + b'\xff\xff'

class IpAddr(bytesOf(16)):
  def ip_str(self):
    if self.startswith(_ZERO_STR10) and self[10:12] == b'\xff\xff':  # ipv4
      return '.'.join(str(i) for i in struct.unpack('>BBBB',self[12:16]))
    else: return ':'.join(('%x' % i) for i in struct.unpack('>HHHHHHHH',self))
  
  @classmethod
  def encode(cls, msg):
    if not isinstance(msg,str):
      return cls(msg[:16])
    
    try:
      groups = [int(i) for i in msg.split('.',maxsplit=4)]
    except ValueError:
      groups = []
    
    if len(groups) == 4:
      succ = True
      for i in groups:    # check number range of item
        if i < 0 or i > 255:
          succ = False
          break
      if succ:
        return cls(_IP_HEAD_STR + struct.pack('>BBBB',*groups),verify=False)
    else:
      groups = msg.split(':')
      if len(groups) >= 2:
        if groups[0] == '' and groups[1] == '':      # starts with ::
          del groups[0]
        elif groups[-1] == '' and groups[-2] == '':  # ends with ::
          del groups[-1]
        if groups.count('') <= 1 and len(groups) <= 8:
          ip_addr = []
          for item in groups:
            if item == '':       # has ::
              ip_addr.extend([ 0 ] * (9 - len(groups)))
            else: ip_addr.append(int(item,16))
          for item in ip_addr:   # check number range of item
            if not (0x0000 <= item <= 0xffff):
              ip_addr = []
              break
          if len(ip_addr) == 8:
            return cls(struct.pack('>HHHHHHHH',*ip_addr),verify=False)
    
    raise ValueError('invalid IP format: %s' % (msg,))

def compose(fields):   # @compose(( ('name',NI), ...)) class MyClass: pass
  assert isinstance(fields,(list,tuple))
  cls = composeOf(fields)
  
  def make_class(sub_cls):
    assert isinstance(sub_cls,type)
    
    class ComposeCls(cls,sub_cls):
      _type_ = sub_cls.__name__
    
    return ComposeCls
  
  return make_class
