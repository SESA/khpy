from kh_root import *
import getpass
import random
import string
import time

class KhProbeFront(KhRoot):
  def __init__(self, configsrc, dbpath):
    KhRoot.__init__(self, configsrc, dbpath)
    self.config = ConfigParser.SafeConfigParser()
    self.config.read(configsrc)

  # cli parser methods   ################################################

  def parse_clean(self, parser):
    parser = KhRoot.parse_clean(self, parser)
    parser.set_defaults(func=self.clean)
    return parser

  def parse_console(self, parser):
    parser = KhRoot.parse_console(self, parser)
    parser.set_defaults(func=self.console)
    return parser

  def parse_get(self, parser):
    parser = KhRoot.parse_get(self, parser)
    parser.set_defaults(func=self.get)
    return parser

  def parse_init(self, parser):
    parser = KhRoot.parse_init(self, parser)
    dcount=0 #self.config.get('Probe','instance_max')
    parser.add_argument('-c', action=KH_store_optional, default=dcount,
        type=int, help='Instance count to initilaize')
    parser.set_defaults(func=self.init)
    return parser

  def parse_install(self, parser):
    parser.set_defaults(func=self.install)
    return parser

  def parse_rm(self, parser):
    parser = KhRoot.parse_rm(self, parser)
    parser.set_defaults(func=self.rm)
    return parser


  # action methods ####################################################

  def clean(self):
    self.forward("clean")
    None

  def console(self):
    self.forward("console")
    None

  def get(self, job, count):
    self.forward_cmd("get "+job+" "+count)

  def rm(self, job):
    self.forward_cmd("rm "+job)

  def init(self, option={}):
    self.forward_cmd("init")

  # utility methods ####################################################
  
  def forward_cmd(self, argstr):
    front = self.config.get('ProbeFront', 'frontsvr')
    ctrl = self.config.get('ProbeFront', 'ctrlexp')
    cmd = "ssh -ttt "+front+" ssh "
    cmd += "$(ssh "+front+" '~/getctlnode "+ctrl+"')"
    cmd += "\" ~/khpy/kh "+argstr+"\""
    print subprocess.check_output(cmd, shell=True)
