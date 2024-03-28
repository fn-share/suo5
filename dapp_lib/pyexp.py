# pyexp.py

__all__ = ['pyexp', 'pyexp_libs', 'PYEXP_STR_MAX', 'PYEXP_LIST_MAX', 'PYEXP_LOOP_MAX']

import sys, os, time, types, traceback

import logging
logger = logging.getLogger(__name__)

#---- expression level interpreter

import importlib
import ast
import operator

PYEXP_STR_MAX  = 262144   # 256K
PYEXP_LIST_MAX = 4096     #   4K
PYEXP_LOOP_MAX = 4096     #   4K

unaryOps = {
  ast.Not: operator.not_,
  ast.USub: lambda x: -x,
}

def _op_add(x, y):
  z = operator.add(x,y)
  if isinstance(z,(tuple,list)):
    assert len(z) <= PYEXP_LIST_MAX, 'out of range'
  elif hasattr(z,'len'):   # str, bytes, such like 'str1' + 'str2'
    assert len(z) <= PYEXP_STR_MAX, 'out of range'
  return z

def _op_mul(x, y):
  z = operator.mul(x,y)
  if hasattr(z,'len'):   # str, bytes, such like 'string' * n
    assert len(z) <= PYEXP_STR_MAX, 'out of range'
  return z

def _op_mod(x, y):
  z = operator.mod(x,y)
  if hasattr(z,'len'):   # str, bytes, such like '%s:%s' % (s1,s2)
    assert len(z) <= PYEXP_STR_MAX, 'out of range'
  return z

binOps = {
  ast.Add: _op_add,      # can check overflow
  ast.Sub: operator.sub,
  ast.Mult: _op_mul,     # can check overflow
  ast.Div: operator.truediv,
  ast.FloorDiv: operator.floordiv,
  ast.Mod: _op_mod,      # can check overflow
  
  ast.BitAnd: lambda x,y: x & y,
  ast.BitOr: lambda x,y: x | y,
  ast.BitXor: lambda x,y: x ^ y,
  
  ast.LShift: operator.lshift,
  ast.RShift: operator.rshift,
  
  ast.Eq: operator.eq,
  ast.NotEq: operator.ne,
  ast.Gt: operator.gt,
  ast.GtE: operator.ge,
  ast.Lt: operator.lt,
  ast.LtE: operator.le,
  
  ast.In: lambda x,y: x in y,
  ast.NotIn: lambda x,y: x not in y,
}

def _import_lib(name, ns):
  if isinstance(name,ast.Name):
    lib_name = name.id
    if isinstance(ns,dict):
      # next will reuse sys.modules[<__package__>.pyexp_libs.<lib_name>]
      plg = importlib.import_module('.pyexp_libs.' + lib_name,package=__package__)
      ns.update(plg._module)
    else:
      logger.warning('no namespace when uses lib (%s)',lib_name)  # no raise exception
  else:
    logger.warning('uses pyexp lib failed')

def _get_name_list(node, out):
  if isinstance(node,ast.Name):
    out.insert(0,node.id)
  elif isinstance(node,ast.Attribute):
    out.insert(0,node.attr)
    return _get_name_list(node.value,out)
  else:
    raise SyntaxError('invalid attribute list')

def _call_fn(obj, name, args, keywords, ns):
  fn = None
  if isinstance(ns,dict):
    if obj is None:
      fn = ns.get(name,None)                  # global function call
    else: fn = ns.get((type(obj),name),None)  # method call
  if fn is None: raise SyntaxError('no function: ' + name)
  
  if isinstance(fn,dict):   # is dict_call, such as: var(a.b) var(a.b,value)
    n = len(args)
    assert n in (1,2), 'invalid dict call'
    
    names = []; obj = fn
    _get_name_list(args[0],names)
    
    if n == 2:    # var(a.b,value)
      last_name = names.pop()
      while names:
        obj = obj[names.pop(0)]
      obj[last_name] = v = _eval(args[1],ns)
      
      assert len(obj) <= PYEXP_LIST_MAX
      return v
    
    else:         # var(a.b)
      while names:
        obj = obj[names.pop(0)]
      return obj
  
  else:
    args = [_eval(arg,ns) for arg in args]
    if obj is not None: args.insert(0,obj)
    if keywords:
      kw = [(item.arg,_eval(item.value,ns)) for item in keywords]
      return fn(*args,**kw)
    else: return fn(*args)

_func_types = (types.FunctionType,types.BuiltinFunctionType,types.BuiltinMethodType,types.MethodDescriptorType)

def _eval(node, ns):
  if isinstance(node,ast.Name):
    if isinstance(ns,dict) and node.id in ns:
      return ns[node.id]
    else: raise SyntaxError('access failed: ' + node.id)
  elif isinstance(node,ast.Attribute):
    obj = _eval(node.value,ns)
    fn = ns.get((type(obj),node.attr),None)     # try find method first
    return getattr(obj,node.attr) if fn is None else fn
  elif isinstance(node,(ast.Str,ast.Bytes)):
    return node.s
  elif isinstance(node,ast.Num):  # int or float
    return node.n
  elif isinstance(node,ast.NameConstant):
    return node.value
  elif isinstance(node,ast.Tuple):
    return tuple(_eval(item,ns) for item in node.elts)
  elif isinstance(node,ast.List):
    return list(_eval(item,ns) for item in node.elts)
  elif isinstance(node,ast.Set):
    return set(_eval(item,ns) for item in node.elts)
  elif isinstance(node,ast.Dict):
    return dict((_eval(k,ns),_eval(v,ns)) for k,v in zip(node.keys,node.values))
  elif isinstance(node,ast.BinOp):
    return binOps[type(node.op)](_eval(node.left,ns), _eval(node.right,ns))
  elif isinstance(node,ast.UnaryOp):
    return unaryOps[type(node.op)](_eval(node.operand,ns))
  elif isinstance(node,ast.Compare):
    return binOps[type(node.ops[0])](_eval(node.left,ns), _eval(node.comparators[0],ns))
  elif isinstance(node,ast.BoolOp):
    if isinstance(node.op,ast.And):   # not call operator.and_ that have no shutcut
      v = _eval(node.values[0],ns)
      return _eval(node.values[1],ns) if v else v
    elif isinstance(node.op,ast.Or):  # not call operator.or_ that have no shutcut
      v = _eval(node.values[0],ns)
      return v if v else _eval(node.values[1],ns)
    else: return binOps[type(node.op)](_eval(node.values[0],ns), _eval(node.values[1],ns))
  elif isinstance(node,ast.IfExp):
    return _eval(node.body,ns) if _eval(node.test,ns) else _eval(node.orelse,ns)
  elif isinstance(node,ast.Expression):
    return _eval(node.body,ns)
  elif isinstance(node,ast.Call):
    fn = node.func
    if isinstance(fn,ast.Name):  # only support: fn_name(...)
      fn_name = fn.id
      if fn_name == 'comma':
        v = None
        for arg in node.args:
          v = _eval(arg,ns)
        return v
      elif fn_name == 'loop':
        args = node.args
        n = len(args)
        assert n >= 1, 'no condition in loop'
        
        cond = args[0]; with_decrease = False; dec_num = 0
        if isinstance(cond,ast.Num):
          dec_num = cond.n
          with_decrease = True
        
        loop_count = 0
        while True:
          if loop_count >= PYEXP_LOOP_MAX: raise RuntimeError('loop out of range')
          if with_decrease:
            if dec_num <= 0: break
            dec_num -= 1
          else:
            cond_value = _eval(cond,ns)
            if not bool(cond_value): break
          
          loop_count += 1
          for i in range(1,n):
            _eval(args[i],ns)
        
        return loop_count      # can be 0..PYEXP_LOOP_MAX
      elif fn_name == 'dir':
        arg = _eval(node.args[0],ns)
        if type(arg) in _func_types:
          ss = getattr(arg,'__name__','')
          if ss[:5] == '_new_':  # it is class
            cls_name = ss[5:]
            return sorted([k[1] for k in ns.keys() if isinstance(k,tuple) and k[0].__name__ == cls_name])
        elif isinstance(arg,dict):
          return sorted([k for k in arg.keys() if isinstance(k,str)])
        return ''
      elif fn_name == 'uses':
        for arg in node.args:
          _import_lib(arg,ns)
        return None
      else:
        return _call_fn(None,fn_name,node.args,node.keywords,ns)
    elif isinstance(fn,ast.Attribute):  # such like: obj.test()
      obj = _eval(fn.value,ns)
      if obj is None: raise SyntaxError('no method: ' + fn.attr)
      return _call_fn(obj,fn.attr,node.args,node.keywords,ns)
    elif isinstance(fn,ast.Call):
      fn = _eval(fn,ns)
      args = [_eval(arg,ns) for arg in node.args]
      return fn(*args)
    
    raise SyntaxError('invalid function call')
  else: raise SyntaxError('operator not support')

def pyexp(s, ns=None):
  node = ast.parse(s,mode='eval')
  return _eval(node.body,ns)

def pyexp_libs(cls, methods=None):
  def regist_fn(fn):
    assert type(fn) == types.FunctionType
    ns = fn.__globals__.get('_module',None)
    if ns is None: fn.__globals__['_module'] = ns = {}
    
    if isinstance(methods,(list,tuple)):
      ns[cls.__name__] = fn     # wrap cls.__init__(...)
      for name in methods:      # wrap cls.methods
        method = getattr(cls,name,None)
        if type(method) == types.MethodDescriptorType:
          ns[(cls,name)] = method
        else: logger.warning('method type mismatch %s.%s',cls.__name__,name)
    else:
      name = methods if isinstance(methods,str) else fn.__name__
      if cls is None:
        ns[name] = fn
      else: ns[(cls,name)] = fn
    return fn
  
  return regist_fn


'''
# from dapp_lib.pyexp import *

assert pyexp('3+4') == 7
assert pyexp('-(3+4)') == -7
assert pyexp('3 < 4')
assert pyexp('not (3 > 4)')
assert pyexp('4 // 3') == 1
assert pyexp('3 / 4') == 0.75
assert pyexp('0x01 |  0x02') == 0x03
assert pyexp('0x01 &  0x02') == 0x00
assert pyexp('0x01 ^  0x02') == 0x03
assert pyexp('[3,4]') == [3,4]
assert pyexp('3 in [3,4]')
assert pyexp('5 not in [3,4]')
assert pyexp('"ab" in [3,4,"ab"]')
assert pyexp('"cd" not in [3,4,"ab"]')
assert pyexp('3 and 1') == 1
assert pyexp('3 or 0') == 3
assert pyexp('3 and 0') == 0
assert pyexp('(3,4+5)') == (3,9)
assert pyexp('{"ab",5}') == {"ab",5}
assert len(pyexp('{"ab":6,5:7}')) == 2
assert pyexp('3 if 1 else 4') == 3
assert pyexp('3 if 0 else 4') == 4

assert pyexp('comma(3,4)') == 4
assert pyexp('upper("abcd")',{'upper':lambda s: s.upper()}) == 'ABCD'
assert pyexp('True or upper("abcd")',{'upper':lambda s: s.upper()}) == True
assert pyexp('name + " OK"',{'name':'wayne'}) == 'wayne OK'

assert pyexp('"ABCD".lower()',{(str,'lower'):str.lower}) == 'abcd'
assert pyexp('name.lower()',{'name':'ABCD',(str,'lower'):str.lower}) == 'abcd'

ns = {'var':{}}
pyexp('uses(basetypes)',ns)
assert pyexp('"abcd".upper()',ns) == 'ABCD'
assert pyexp('var.set("name","wayne")',ns) == 'wayne'
assert pyexp('var.get("name")',ns) == 'wayne'
pyexp('var.set("info",{"age":20})',ns)
assert pyexp('var.get("info").get("age")',ns) == 20

pyexp('dir(str)',ns)
pyexp('dir({"age":20})',ns)

ns = {'var':{}}
pyexp('uses(basetypes)',ns)
pyexp('var(info,{"age":20})',ns)
assert pyexp('var(info.age)',ns) == 20
assert pyexp('var(info.age,21)',ns) == 21
assert pyexp('var(info.age)',ns) == 21

ns = {'var':{}}
pyexp('uses(basetypes)',ns)
pyexp('var(count,0)',ns)
pyexp('loop(2,log("in loop"))',ns)
pyexp('loop(var(count) < 5,var(count,var(count)+1),log("in loop",var(count)))',ns)
'''
