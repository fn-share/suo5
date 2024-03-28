# local_web.py

import os

from .dapp_http import _app as app
assert app is not None, 'please call dapp_http.config_http() first'

from . import runtime
APP_NAME = runtime.get('APP_NAME','')

__all__ = [ 'app', 'APP_NAME', 'get_url_root' ]

from flask import request

def get_url_root():
  host = request.headers.get('Host')
  sub_domain = request.headers.get('X-Sub-Domain')
  prefix = '/' + APP_NAME + '/'
  
  if host and sub_domain:        # from API Gateway
    proto = request.headers.get('X-Forwarded-Proto','http')
    return '%s://%s/%s%s' % (proto,host,sub_domain,prefix)
  else:
    # if 'X-Nbc-Sn' in request.headers: pass  # from tr-client
    # else: pass  # visit from listen address
    return prefix


#----

from urllib.parse import urljoin

def _favicon():
  return app.send_static_file('favicon.ico')

def _index_page():
  url = urljoin(get_url_root(),'static/index.html')
  return ('',302,{'Location':url})

def _is_alive():
  return 'OK'

@app.route('/favicon.ico')
def favicon():
  return _favicon()

@app.route('/')
@app.route('/index.html')
def index_page():
  return _index_page()

@app.route('/is_alive')
def is_alive():
  return _is_alive()
