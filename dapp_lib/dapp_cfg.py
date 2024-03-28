# dapp_cfg.py

import os, json

class DappConfig(dict):
  def __init__(self, mapping=None, cfg_file='', readonly=True):
    if mapping is None: mapping = {}
    super().__init__(mapping)
    
    self.cfg_file = cfg_file
    self.readonly = readonly
  
  def path_join(self, sub=''):
    assert self.cfg_file, 'config not load yet'
    return os.path.join(os.path.split(self.cfg_file)[0],sub)
  
  @staticmethod
  def load(dapp, readonly, org_cfg_file='./config.json', factory='.red-brick'):
    targ_loc = os.path.join(os.path.expanduser('~'),factory,dapp)
    os.makedirs(targ_loc,exist_ok=True)
    
    # target file: ~/.red-brick/<dapp>/config.json
    targ_file = os.path.join(targ_loc,'config.json')
    if not os.path.isfile(targ_file):   # if no target file, try copy first
      if os.path.isfile(org_cfg_file):
        with open(org_cfg_file,'rt') as f:
          ctx = f.read()
      else: ctx = '{}'
      with open(targ_file,'wt') as f:
        f.write(ctx)
    
    with open(targ_file,'rt') as f:
      d = json.load(f)   # load JSON successful
      return DappConfig(d,targ_file,readonly)
  
  def save(self):
    assert self.cfg_file, 'config not load yet'
    assert not self.readonly, 'can not write readonly file'
    
    s = json.dumps(self,indent=2)
    with open(self.cfg_file,'wt') as f:
      f.write(s)
