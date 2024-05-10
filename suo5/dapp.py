# dapp.py

import logging
logger = logging.getLogger(__name__)

import os, time, struct, base64, json, traceback
from threading import Thread, Timer
from binascii import unhexlify
from urllib.request import urlopen

#----

_last_cred = ''       # current in using credential
_newest_cred = ''     # newest credential when it re-applied
_relay_server = None  # suo5 server: (ip:port)

suo5_server_url = ''  # https://.../stream
suo5_server_ip  = ''

_rb_var_root = os.path.join(os.path.expanduser('~'),'red-brick','var')
os.makedirs(_rb_var_root,exist_ok=True)

_rb_log_root = os.path.join(os.path.expanduser('~'),'red-brick','log')
os.makedirs(_rb_log_root,exist_ok=True)

def is_server_cfg_ok():
  return isinstance(suo5_server_url,str) and suo5_server_url[:4] == 'http'  # http or https

def when_cred_updated(now_tm, keycode, relay_server):
  global _newest_cred, _relay_server
  
  try:
    _newest_cred = base64.b64encode(now_tm.to_bytes(4,'big') + unhexlify(keycode)).decode('utf-8')
    
    if auto_start_suo5 and is_server_cfg_ok():
      _relay_server = (relay_server[0],8000)
      if not _last_cred:
        pid_str = find_suo5_PID()
        if pid_str:
          os.popen('kill -9 ' + pid_str).read()   # ensure only one suo5 client in running
          logger.info('old suo5 client is killed.')
        Timer(1,start_suo5_client).start()
      else: check_alive.check_right_now = True
  except: pass

#----

from . import runtime

_check_token_ok = runtime['check_token_ok']

auto_start_suo5 = bool(runtime['config'].get('auto_start_suo5',False))

suo5_local_host = ''  # 0.0.0.0:49000
find_client_pid = ''  # ps -ef | grep 'suo5 -t http' | grep -v grep | awk '{print $2}'
client_user_psw = ''  # 'user:password' or ''

ex_opt = {}  # {disable_check,with_get_method,with_no_gzip,with_cookiejar,user_agent}

_suo5_bin_list = {
  ('darwin','x86_64'): 'suo5-darwin-amd64',  # mac x86
  ('linux','x86_64'): 'suo5-linux-amd64',    # linux x86
  ('linux','aarch64'): 'suo5-linux-arm64' }  # linux arm
suo5_bin = None

def init_suo5():
  global suo5_bin
  global auto_start_suo5, suo5_server_url
  global suo5_local_host, find_client_pid, client_user_psw, ex_opt
  
  uname = os.popen('uname -sm').read()  # 'Darwin x86_64' 'Linux aarch64' 'Linux x86_64'
  uname = tuple(uname.lower().split())
  suo5_bin = _suo5_bin_list.get(uname,None)
  if suo5_bin is None:
    logger.error('suo5 client not support platform: %s',uname)
    return False
  
  cfg = runtime['config']
  suo5_server_url = cfg.get('suo5_server_url','')
  suo5_local_host = cfg.get('suo5_local_host','')
  find_client_pid = cfg.get('find_client_pid','')
  client_user_psw = cfg.get('client_user_psw','')
  ex_opt = cfg.get('ex_opt',{})
  
  if not suo5_local_host or len(suo5_local_host.split(':')) != 2:
    logger.error('invalid "suo5_local_host" in config.json')
    auto_start_suo5 = False  # meet error, avoid auto start
    return False
  if not find_client_pid:
    logger.error('invalid "find_client_pid" in config.json')
    auto_start_suo5 = False  # meet error, avoid auto start
    return False
  if not ex_opt.get('user_agent',''):
    logger.error('invalid "exopt.user_agent" in config.json')
    auto_start_suo5 = False  # meet error, avoid auto start
    return False
  
  import atexit
  check_alive.start()
  atexit.register(lambda: check_alive.exit())
  
  logger.info('load config successful: suo5=%s, auto=%s, check_alive=%s',suo5_bin,auto_start_suo5,not ex_opt.get('disable_check',False))
  return True

def find_suo5_PID():
  return os.popen(find_client_pid).read()

FIXED_SUO5_UA = 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.1.2.3'

def start_suo5_client():
  global _last_cred, suo5_server_ip
  
  if not suo5_server_ip and suo5_server_url:
    if not ex_opt.get('with_get_method',False):  # use POST method
      try:
        b = urlopen(suo5_server_url,timeout=10).read()[:64].split(b',')
        if len(b) >= 3 and b[0] == b'OK':
          suo5_server_ip = b[1].decode('utf-8')
      except: pass
  
  ua = ex_opt.get('user_agent')
  if ua == FIXED_SUO5_UA or ex_opt.get('disable_check',False):
    ex_arg = "--ua '%s' " % (ua,)
  else: ex_arg = "--ua '%s %s' " % (ua,_newest_cred)
  
  if client_user_psw:
    ex_arg += "--auth '%s' " % (client_user_psw,)
  if ex_opt.get('with_get_method',False):
    ex_arg += '--method GET '
  if ex_opt.get('with_no_gzip',False):
    ex_arg += '--no-gzip '
  if ex_opt.get('with_cookiejar',False):
    ex_arg += '--jar '
  
  log_file = os.path.join(_rb_log_root,'suo5.out')
  sh_cmd = "nohup ./suo5/%s -t %s -l %s %s 2>&1 >%s &" % (suo5_bin,suo5_server_url,suo5_local_host,ex_arg,log_file)
  for i in range(2):    # try 2 times
    os.popen(sh_cmd).read()
    time.sleep(2)
    if find_suo5_PID():
      _last_cred = _newest_cred
      logger.info('suo5 client is starting ...')
      return True
  return False

def check_suo5_alive():
  if not _last_cred: return False
  if ex_opt.get('disable_check',False): return True  # avoid alive check, take as aliving
  
  user_agent = ex_opt.get('user_agent')
  if client_user_psw:
    auth_arg = '-U %s ' % (client_user_psw,)
  else: auth_arg = ''
  sh_cmd = 'curl -s %s--max-time 10 -H "User-Agent: %s %s" -x socks5h://%s %s' % (auth_arg,user_agent,_last_cred,suo5_local_host,suo5_server_url)
  
  try:
    for i in range(3):    # max try 3 times
      if os.popen(sh_cmd).read()[:2] == 'OK':
        return True
      time.sleep(2)
  except: pass
  return False

'''
from python_socks import ProxyTimeoutError
from python_socks.sync import Proxy

def check_suo5_alive():
  if not _relay_server: return False
  if not _last_cred: return False
  if ex_opt.get('disable_check',False): return True  # avoid alive check, take as aliving
  
  user_agent = ex_opt.get('user_agent')
  data = 'GET / HTTP/1.1\r\nConnection: close\r\nUser-Agent: %s %s\r\n\r\n' % (user_agent,_last_cred)
  data = data.encode('utf-8')
  
  for i in range(3):  # max try 3 times
    try:
      proxy = Proxy.from_url('socks5://' + suo5_local_host)
      sock = proxy.connect(dest_host=_relay_server[0],dest_port=_relay_server[1],timeout=10)
      sock.sendall(data)
      s = sock.recv(4096)
      idx = s.find(b'\r\n\r\n')
      if idx > 0 and s[idx+4:idx+6] == b'OK':
        return True
    except ProxyTimeoutError:
      pass    # will try again
    except:
      # logger.warning(traceback.format_exc())
      time.sleep(2)
      break
  
  return False  '''

class CheckAlive(Thread):
  def __init__(self):
    Thread.__init__(self)
    self._active = True
    self.daemon = True
    self.check_right_now = False
  
  def exit(self):
    self._active = False
    if self.is_alive():
      self.join()
  
  def run(self):
    tr_login_file = os.path.join(_rb_var_root,'.tr_login')
    tr_login_time = 0
    
    counter = 0
    while self.is_alive() and self._active:
      counter += 1
      
      # check login changing every 40 seconds
      if counter % 8 == 4 and not ex_opt.get('disable_check',False):
        try:
          if os.path.isfile(tr_login_file):
            modi_tm = os.stat(tr_login_file).st_mtime
            if tr_login_time != modi_tm:
              tr_login_time = modi_tm
              
              line = ''
              b = open(tr_login_file,'rt').read().splitlines()
              s = ',' + suo5_server_ip + ','
              for ln in b:
                if ln.find(s) > 0:
                  line = ln
                  break
              
              b2 = line.split(',')
              if len(b2) == 4:  # should be: "now,keycode,server_ip,server_port"
                server = (b2[2],int(b2[3]))
                when_cred_updated(int(b2[0]),b2[1],server)
        except:
          logger.warning(traceback.format_exc())
      
      # check suo5 connection every 60 seconds normally
      if _relay_server and (self.check_right_now or (counter % 12) == 11):
        self.check_right_now = False
        counter = (counter // 12) * 12
        
        if auto_start_suo5 and is_server_cfg_ok():
          try:
            # step 1: check suo5 connection is OK or not
            is_alive = check_suo5_alive()
            
            if not is_alive:     
              # setp 2: find PID and kill it when connection broken
              pid_str = find_suo5_PID()
              if pid_str:
                os.popen('kill -9 ' + pid_str).read()
                time.sleep(1)
              
              # step 3: try restart suo5 client
              if not find_suo5_PID():    # no suo5 client application
                start_suo5_client()
          except:
            logger.warning(traceback.format_exc())
      
      time.sleep(5)
    
    self._active = False
    logger.info('CheckAlive thread exited')

check_alive = CheckAlive()

#----

from flask import request, make_response

from .local_web import *    # import app, APP_NAME, get_url_root
assert app is not None, 'please call dapp_http.config_http() first'

_hostname = ''

def _suo5_get_state():
  global _hostname
  if not _hostname:
    _hostname = os.popen('hostname').read().strip()
    if _hostname[-6:].lower() != '.local': _hostname += '.local'
  
  cfg = runtime['config']
  return { 'active': bool(find_suo5_PID()),
    'hostname': '%s:%s' % (_hostname,suo5_local_host.split(':')[-1]),
    'auto_start': bool(cfg.get('auto_start_suo5',False)),
    'user_password': cfg.get('client_user_psw',''),
    'server_url': cfg.get('suo5_server_url',''),
    'ex_opt': cfg.get('ex_opt',{}) }

@app.route('/state', methods=['GET','POST'])
def suo5_get_state():
  try:
    if request.method == 'GET':
      return _suo5_get_state()
    
    else:  # is POST
      if not _check_token_ok(request): return ('INVALID_TOKEN',401)
      
      data = request.get_json(force=True,silent=True)
      new_state = data.get('state','')
      if new_state == 'CLOSED':
        pid_str = find_suo5_PID()
        if pid_str:
          logger.info('try stop suo5 client.')
          os.popen('kill -9 ' + pid_str).read()
      elif new_state == 'RUNNING':
        if not find_suo5_PID():
          start_suo5_client()
      return {'result':'success'}
  
  except:
    logger.warning(traceback.format_exc())
  return ('FORMAT_ERROR',400)

@app.route('/change_config', methods=['POST'])
def suo5_change_cfg():
  global auto_start_suo5, suo5_server_url, client_user_psw
  
  try:
    if not _check_token_ok(request): return ('INVALID_TOKEN',401)
    
    # step 1: check args
    data = request.get_json(force=True,silent=True)
    server_url = data.get('server_url','')
    user_passw = data.get('user_password','')
    auto_start = bool(data.get('auto_start',False))
    if not server_url or (user_passw and len(user_passw.split(':')) != 2):
      return ('INVALID_PARAMETER',400)
    
    # step 2: change global variables
    cfg = runtime['config']
    auto_start_suo5 = cfg['auto_start_suo5'] = auto_start
    suo5_server_url = cfg['suo5_server_url'] = server_url
    client_user_psw = cfg['client_user_psw'] = user_passw
    
    # step 3: save config.json
    cfg.save()
    
    # step 4: try restart suo5 client
    pid_str = find_suo5_PID()
    if pid_str:
      logger.info('try stop suo5 client.')
      os.popen('kill -9 ' + pid_str).read()
    
    if auto_start and not find_suo5_PID():
      start_suo5_client()
    
    return {'result':'success'}
  except:
    logger.warning(traceback.format_exc())
  return ('FORMAT_ERROR',400)

@app.route('/change_exopt', methods=['POST'])
def suo5_change_exopt():
  global ex_opt
  
  try:
    if not _check_token_ok(request): return ('INVALID_TOKEN',401)
    
    # step 1: check args
    data = request.get_json(force=True,silent=True)
    disable_check = bool(data.get('disable_check',False))
    with_get_method = bool(data.get('with_get_method',False))
    with_no_gzip = bool(data.get('with_no_gzip',False))
    with_cookiejar = bool(data.get('with_cookiejar',False))
    user_agent = data.get('user_agent','')
    
    # step 2: change global variables
    cfg = runtime['config']
    ex_opt = cfg['ex_opt'] = { 'disable_check':disable_check, 'with_get_method':with_get_method,
      'with_no_gzip':with_no_gzip, 'with_cookiejar':with_cookiejar, 'user_agent':user_agent }
    
    # step 3: save config.json
    cfg.save()
    
    # step 4: try restart suo5 client
    pid_str = find_suo5_PID()
    if pid_str:
      logger.info('try stop suo5 client.')
      os.popen('kill -9 ' + pid_str).read()
    
    if cfg.get('auto_start_suo5',False) and not find_suo5_PID():
      start_suo5_client()
    
    return {'result':'success'}
  except:
    logger.warning(traceback.format_exc())
  return ('FORMAT_ERROR',400)


#----
init_suo5()
