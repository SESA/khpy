from kh_base import *

class KhQemu(KhBase):
  def __init__(self, configsrc):
    KhBase.__init__(self, configsrc)

  # misc
  def test(self):
    print "You found qemu!"

  def parse_get(self, parser):
    parser = KhBase.parse_get(self, parser)
    parser.add_argument('bootimg', action=Parameterize,
        help='Path to boot image')
    parser.set_defaults(func=self.get)
    return parser

  def parse_rm(self, parser):
    parser = KhBase.parse_rm(self, parser)
    parser.set_defaults(func=self.rm)
    return parser

  def parse_setup(self, parser):
    parser = KhBase.parse_setup(self, parser)
    parser.set_defaults(func=self.setup)
    return parser

  def get(self, job, count, bootimg ):
    KhBase.get(self, job, count)
    print "qemu get"
  def rm(self, job):
    # want to do cleanup here before calling KhBase
    KhBase.rm(self, job)
    print "qemu rm"
  def setup(self):
    KhBase.setup(self)
    print "qemu setup"
