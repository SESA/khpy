##########################################
#  Kittyhawk Command-line Interface      #
#  - environment verification and setup  #
##########################################
import sys
import os
from kh_platform import *

# verify environment variables 
required_vars = ["KHDB", "KHTYPE"]
missing_vars = False
for i in required_vars:
  if os.getenv(i) == None:
    print "Error: missing environment variable",i
    missing_vars = True
if missing_vars:
  exit()
  
# Detect and setup envoirnment settings
def setup_environment():
  ''' add additional platforms below
      e.g., moc, ec2 .. 
  '''
  env = os.getenv("KHTYPE")
  # qemu-kvm
  if env == "qemu":
    from kh_qemu import *
    ret = KhQemu()
  # hpcloud
  elif evn  == "hpcloud":
    from kh_hpcloud import *
    ret = KhHpCloud()
  # default 
  else:
    ret = KhBase()
  return ret
