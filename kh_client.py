from kh_root import *
import getpass
import random
import string
import time

class KhClient(KhRoot):
  def __init__(self, configsrc, dbpath):
    KhRoot.__init__(self, configsrc, dbpath)
    self.config = ConfigParser.SafeConfigParser()
    self.config.read(configsrc)

  # cli parser methods   ################################################

  def parse_alloc(self, parser):
    parser = KhRoot.parse_alloc(self, parser)
    parser.set_defaults(func=self.alloc)
    return parser

  def parse_clean(self, parser):
    parser = KhRoot.parse_clean(self, parser)
    parser.set_defaults(func=self.clean)
    return parser

  def parse_console(self, parser):
    parser = KhRoot.parse_console(self, parser)
    parser.set_defaults(func=self.console)
    return parser

  def parse_info(self, parser):
    parser.set_defaults(func=self.info)
    return parser

  def parse_init(self, parser):
    parser = KhRoot.parse_init(self, parser)
    dcount=0 
    parser.add_argument('-c', action=KH_store_optional, default=dcount,
        type=int, help='Instance count to initilaize')
    parser.set_defaults(func=self.init)
    return parser

  def parse_network(self, parser):
    parser.set_defaults(func=self.network)
    return parser

  def parse_install(self, parser):
    parser.set_defaults(func=self.install)
    return parser

  def parse_remove(self, parser):
    parser = KhRoot.parse_rm(self, parser)
    parser.set_defaults(func=self.remove)
    return parser


  # action methods ####################################################

  def alloc(self, job, count):
    self.forward_cmd("get "+str(job)+" "+str(count))

  def clean(self):
    self.forward_cmd("clean")
    None

  def console(self):
    self.forward_cmd("console")
    None

  def init(self, option={}):
    self.forward_cmd("init")

  def info(self, option={}):
    self.forward_cmd("info")

  def rm(self, job):
    self.forward_cmd("rm "+str(job))


  # utility methods ####################################################
  
  def forward_cmd(self, argstr):
    print "Not yet implemented"
    #front = self.config.get('ProbeFront', 'frontsvr')
    #ctrl = self.config.get('ProbeFront', 'ctrlexp')
    #cmd = "ssh -ttt "+front+" ssh "
    #cmd += "$(ssh "+front+" '~/getctlnode "+ctrl+"')"
    #cmd += "\" ~/khpy/kh "+argstr+"\""
    #print subprocess.check_output(cmd, shell=True)
