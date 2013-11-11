from kh_base import *

class KhHpCloud(KhBase):
  def __init__(self, configsrc):
    KhBase.__init__(self, configsrc)

  # misc
  def test(self):
    print "You found hp!"

  def parse_get(self, parser):
    parser.set_defaults(func=self.get)
    parser.set_defaults(func=self.get)
    parser.add_argument('job', action=Parameterize, metavar="arg")
    parser.add_argument('count', action=Parameterize, metavar="arg")
    parser.add_argument('--option', action=Parameterize, metavar="arg",
        type=int, nargs=1, help='an integer for the accumulator')
    return parser

  def parse_rm(self, parser):
    parser.set_defaults(func=self.rm)
    return parser
  def parse_setup(self, parser):
    parser.set_defaults(func=self.setup)
    return parser

  def get(self, job, count, option=0):
    KhBase.get(self, job, count)
    print "hp get", job, count, option

  def rm(self):
    print "hp rm"
  def setup(self):
    KhBase.setup(self)
    print "hp setup"
