from kh_base import *

class KhQemu(KhBase):
  def __init__(self, configsrc):
    KhBase.__init__(self, configsrc)

  # misc
  def test(self):
    print "You found qemu!"

  def parse_get(self, parser):
    parser.set_defaults(func=self.get)
    return parser
  def parse_rm(self, parser):
    parser.set_defaults(func=self.rm)
    return parser
  def parse_setup(self, parser):
    parser.set_defaults(func=self.setup)
    return parser

  def get(self):
    print "qemu get"
  def rm(self):
    print "qemu rm"
  def setup(self):
    print "qemu setup"
