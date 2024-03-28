# dapp_conn.py

import traceback

from twisted.internet import reactor, error
from twisted.web import server, http

import logging
logger = logging.getLogger(__name__)


#----

class HttpCtrlBlock(object):
  def __init__(self, http_entry, conn_num, cred_pub, cred_str1, cred_str2, cred_sig):
    self.http_entry = http_entry  # str
    self.conn_num  = conn_num     # int
    self.cred_pub  = cred_pub     # bytes
    self.cred_str1 = cred_str1    # bytes
    self.cred_str2 = cred_str2    # bytes
    self.cred_sig  = cred_sig     # bytes
    
    self.conns = []

# assume that self._conn_buff save incoming data
# assume that self.process_msg(first_ln,raw_headers,head_size,msg)
def _recv_one_http(self, data):
  self._conn_buff = data = self._conn_buff + data
  
  try:
    while True:
      msg_size = len(data)
      if not msg_size: break
      
      head_end = data.find(b'\r\n\r\n')
      if head_end < 0:
        if msg_size > 4096:   # max header size is 4096
          self._conn_buff = b''
          logger.debug('drop package: size=%s',msg_size)
        # else, wait receiving more
        return
      
      heads = data[:head_end].splitlines()
      first_ln = heads.pop(0)
      
      body_len = 0; raw_headers = []
      try:
        for item in heads:
          b = item.split(b':',maxsplit=1)
          if len(b) != 2: continue
          one_key = b[0].strip().upper()
          one_value = b[1].strip()
          if one_key == b'CONTENT-LENGTH':
            body_len = int(item[16:])
          raw_headers.append((one_key,one_value))
      except: body_len = -1
      
      if body_len < 0:
        self._conn_buff = b''
        logger.debug('drop package: invalid header')
        return
      if body_len > 0x1000000:   # max http package size is 16M
        self._conn_buff = b''
        logger.debug('drop package: size=%s, exceed max size',body_len)
        return
      
      pkg_size = head_end + 4 + body_len
      if pkg_size > msg_size:
        return   # wait receiving more
      self._conn_buff = next_one = data[pkg_size:]
      
      try:
        self.process_msg(first_ln,raw_headers,head_end+4,data[:pkg_size])
      except:
        logger.debug(traceback.format_exc())
      
      data = next_one  # try next package
  
  except: logger.debug(traceback.format_exc())

class MyHTTPChannelProtocol(http._GenericHTTPChannelProtocol):
  def connectionMade(self):
    self.timeOut = 600          # default closed after 10 minutes, it would affected by 'Connection: close' header
    super().connectionMade()    # this line actually do nothing
    try:
      self.transport.setTcpKeepAlive(1)  # default transport.getTcpKeepAlive() is False
      # self.transport.setTcpNoDelay(1)  # quick responsive for small package
    except: logger.debug(traceback.format_exc())
    self.transport._curr_sequence = 0
    
    self._conn_buff  = b''
    self._first_recv = True
    reactor.callLater(30,self.check_allocate)
  
  def check_allocate(self):
    if self._first_recv:
      self.transport.abortConnection()
  
  def connectionLost(self, reason):
    if not reason.check(error.ConnectionClosed):
      logger.info('inner connection broken: reason=%s',reason.value)
    else: logger.debug('inner connection lost: %s',reason.value)
    
    trans_id = id(self.transport)
    for idx,transport in enumerate(self.HCB.conns):
      if id(transport) == trans_id:
        try:
          self.HCB.conns.pop(idx)   # safe remove connections
        except: pass
        break
      idx += 1
  
  def dataReceived(self, data):
    _recv_one_http(self, data)
  
  def process_msg(self, first_ln, raw_headers, head_size, msg):
    logger.debug('recv http (size=%s): %s',len(msg),first_ln)
    
    if self._first_recv:
      self._first_recv = False
      
      succ = False
      b = first_ln.split(b' ')
      if len(b) == 3:
        url = b[1]
        if url == b'/SUCC':
          conn_num = 1; entry = b''
          for k,v in raw_headers:
            if k == b'X-CONNECTION-NUM':
              conn_num = int(v)   # real allowed connection number
            elif k == b'X-ENTRY':
              entry = v
          
          self.HCB.conn_num = conn_num
          self.HCB.http_entry = entry.decode('utf-8')
          self.HCB.conns.append(self.transport)
          logger.info('tcp channel is allocated: num=%i, entry=%s',conn_num,self.HCB.http_entry)
          succ = True
        else: logger.warning('allocate tcp channel failed: %s',url[1:].decode('utf-8'))
      
      if not succ: self.transport.abortConnection()
    
    else:
      sn = None
      for k,v in raw_headers:
        if k == b'X-NBC-SN':
          sn = int(v)
          break
      
      if isinstance(sn,int):
        self.transport._curr_sequence = sn
        super().dataReceived(msg)

class MyHttpChannel(http.HTTPChannel):
  def checkPersistence(self, request, version):
    # return super().checkPersistence(request,version)
    return True  # avoid header of 'Connection: close' close the channel
  
  def allContentReceived(self):
    # logger.debug('> %s %s',self._command.decode('utf-8'),self._path.decode('utf-8'))
    super().allContentReceived()
  
  def writeHeaders(self, version, code, reason, headers):
    headers.insert(0,(b'X-Nbc-Sn',b'%i' % self.transport._curr_sequence))
    super().writeHeaders(version,code,reason,headers)
  
  def requestDone(self, request):
    super().requestDone(request)
    # logger.debug('< %i %s, %i bytes',request.code,request.code_message.decode('utf-8'),request.sentLength)

def _myHTTPChannelProtocolFactory(self):
  return MyHTTPChannelProtocol(MyHttpChannel())

class MyHttpFactory(server.Site):
  protocol = _myHTTPChannelProtocolFactory
  
  def __init__(self, resource, HCB):
    self.HCB = HCB
    server.Site.__init__(self,resource)
  
  def buildProtocol(self, addr):
    channel = super().buildProtocol(addr)  # channel is instance of MyHTTPChannelProtocol
    channel.transport = self.transport
    channel.HCB = self.HCB
    channel.connectionMade()
    
    # request TCP-RELAY allocate
    request = b'GET /allocate HTTP/1.1\r\nX-Cred0: %s\r\nX-Cred1: %s\r\nX-Cred2: %s\r\nX-Cred3: %s\r\n\r\n' % (
      self.HCB.cred_pub, self.HCB.cred_str1, self.HCB.cred_str2, self.HCB.cred_sig )
    self.transport.writeSomeData(request)  # use writeSomeData, not write()
    
    return channel
  
  def startedConnecting(self, connector):
    # logger.info('http connecting to (%s:%s)',connector.host,connector.port)
    self.transport = connector.transport
  
  def clientConnectionFailed(self, connector, reason):
    # logger.info('http connection (%s:%s) failed: %s',connector.host,connector.port,reason.value)
    pass
  
  def clientConnectionLost(self, connector, reason):
    # logger.info('lost http connection (%s:%s): %s',connector.host,connector.port,reason.value)
    pass
  
  def doStop(self):
    super().doStop()
    # logger.info('http connection stopped')
