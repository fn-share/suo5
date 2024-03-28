# tee/__init__.py

import sys
if sys.version_info.major < 3:
  raise Exception('only support python v3+')

runtime = {}    # runtime configure
