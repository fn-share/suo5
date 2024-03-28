# lcns_loader.py

from nbc import wallet
from dapp_lib.formatter import *

__all__ = [ 'load_end_lcns' ]

TAG_AUTH_ACCOUNT = 0xc0
TAG_DIST_ACCOUNT = 0xc1
TAG_RESOURCE_ID  = 0xc2
TAG_AMOUNT       = 0xc3
TAG_EXPIRED      = 0xc4
TAG_BODY         = 0xc5
TAG_TARG_ACCOUNT = 0xc6
TAG_SUB_LCNS     = 0xc7
TAG_PREV_HASH    = 0xc8
TAG_SEED_SECRET  = 0xc9
TAG_SIGNATURE    = 0xca

def ber_encode(tag, b):  # tag should be 0xc0~0xdf, b should be bytes
  i = len(b)             # len(b) must less than 65536
  if i > 255:
    hi,lo = divmod(i,256)
    return bytes((tag,0x82,hi,lo)) + b
  elif i > 127:
    return bytes((tag,0x81,i)) + b
  else: return bytes((tag,i)) + b

def ber_decode(b):       # b should be bytes
  ret = []
  
  i = 0; iLen = len(b)   # len(b) must less than 65536
  while i < iLen:
    tag = ord(b[i:i+1])
    i += 1
    if i >= iLen:
      raise Exception('BER out of range')
    
    i2 = ord(b[i:i+1])
    if i2 == 0x82:
      subLen = (ord(b[i+1:i+2]) << 8) + ord(b[i+2:i+3])
      i += 3
    elif i2 == 0x81:
      subLen = ord(b[i+1:i+2])
      i += 2
    else:
      if i2 > 0x80: raise Exception('BER format error')
      subLen = i2
      i += 1
    
    if i + subLen > iLen:
      raise Exception('BER out of range')
    ret.append((tag,b[i:i+subLen]))
    i += subLen
  
  return ret

def load_end_lcns(lcns_bytes, body_cls, amount_cls):
  assert lcns_bytes[:4] == b'lcn1', 'invalid lcn1 format'
  idx = lcns_bytes.find(b'lcn2\xc8\x20')
  lcn1_ctx = lcns_bytes[:idx if idx > 0 else None]
  
  lcn1 = dict(ber_decode(lcn1_ctx[4:]))
  body = lcn1.get(TAG_BODY,b'')
  sig1 = lcn1.get(TAG_SIGNATURE,b'')
  auth = lcn1.get(TAG_AUTH_ACCOUNT,b'')
  owner = lcn1.get(TAG_DIST_ACCOUNT,b'') or auth
  assert len(auth) == 33 and len(owner) == 33
  
  wa1 = wallet.Address(pub_key=auth);
  if not wa1.verify_ex(lcns_bytes[:idx-len(sig1)-2],sig1,no_der=True):
    raise RuntimeError('invalid lcn1 signature')
  
  lcn2_ctx = b''
  if idx > 0:  # have lcn2
    lcn2_ctx = lcns_bytes[idx:]
    lcn2 = dict(ber_decode(lcn2_ctx[4:]))
    
    sig2 = lcn2.get(TAG_SIGNATURE,b'')
    if auth == owner:
      wa2 = wa1
    else: wa2 = wallet.Address(pub_key=owner);
    if not wa2.verify_ex(lcns_bytes[idx:-2-len(sig2)],sig2,no_der=True):
      raise RuntimeError('invalid lcn2 signature')
    
    targ = lcn2.get(TAG_TARG_ACCOUNT,b'')
    amount = lcn2.get(TAG_AMOUNT,b'') or lcn1.get(TAG_AMOUNT,b'')
    expired = lcn2.get(TAG_EXPIRED,b'') or lcn1.get(TAG_EXPIRED,b'')
  else:  # no lcn2
    lcn2 = None
    targ = lcn1.get(TAG_TARG_ACCOUNT,b'')
    amount = lcn1.get(TAG_AMOUNT,b'')
    expired = lcn1.get(TAG_EXPIRED,b'')
  assert len(targ) == 33, 'no TARG_ACCOUNT field'
  
  if body: body = body_cls.decode(body)
  if amount: amount = amount_cls.decode(amount)
  return (lcn1,lcn2,body,amount,expired,lcn1_ctx,lcn2_ctx,auth,owner,targ)
