# dapp_http.py

import hashlib
from binascii import hexlify

from twisted.internet import reactor
from twisted.web.wsgi import WSGIResource

from dapp_lib.dapp_conn import HttpCtrlBlock, MyHttpFactory

_app = None
_flask_site = None

def config_http(static_dir=None, static_url=None):
  global _app, _flask_site
  if _app: return _app
  
  import os
  from flask import Flask
  folder = static_dir or os.path.abspath('./static')
  url = static_url or '/static'
  _app = Flask(__name__,static_folder=folder,static_url_path=url)
  _flask_site = WSGIResource(reactor,reactor.getThreadPool(),_app)
  
  return _app

def check_connections(relay_serv, HCB):
  # step 1: try add more connections
  if len(HCB.conns) < HCB.conn_num:
    reactor.connectTCP(relay_serv[0],relay_serv[1],MyHttpFactory(_flask_site,HCB),timeout=30)
  
  # step 2: set checking later, run every 90 seconds
  reactor.callLater(90,check_connections,relay_serv,HCB)

def start_web_service(relay_serv, lcns_info, conn_nonce=None, app_name=None):
  if lcns_info:
    conn_num = lcns_info[3]._._conn_num
    cred_1 = hexlify(lcns_info[5])
    cred_2 = hexlify(lcns_info[6])
    HCB = HttpCtrlBlock('',conn_num,b'',cred_1,cred_2,b'')
  elif isinstance(conn_nonce,int):      # conn_nonce is connection num  # debug mode
    assert isinstance(app_name,str) and app_name
    cred_1 = ('name:%s,period:1,num:%i' % (app_name,conn_nonce)).encode('utf-8')
    cred_sig = nonce = hexlify(b'null')
    HCB = HttpCtrlBlock('',conn_nonce,b'BUILTIN',cred_1,nonce,cred_sig)
  else:
    assert isinstance(conn_nonce,bytes) and len(conn_nonce) >= 5
    assert isinstance(app_name,str) and app_name
    
    cred_1 = ('name:%s,period:1,num:1' % app_name).encode('utf-8')  # careful! num fixed to 1
    cred_sig = hashlib.sha256(hashlib.sha256(cred_1).digest()+b':'+conn_nonce).digest()[:4]
    HCB = HttpCtrlBlock('',1,b'BUILTIN',cred_1,hexlify(conn_nonce),hexlify(cred_sig))
  
  reactor.connectTCP(relay_serv[0],relay_serv[1],MyHttpFactory(_flask_site,HCB),timeout=30)
  reactor.callLater(40,check_connections,relay_serv,HCB)
  
  return HCB
