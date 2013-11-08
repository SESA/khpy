from kh_base import *

class KhHpCloud(KhBase):
  def __init__(self):
    None

  # misc
  def test(self):
    print "You found hp!"

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
    print "hp get"
  def rm(self):
    print "hp rm"
  def setup(self):
    print "hp setup"
