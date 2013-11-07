##########################################
#  Kittyhawk Command-line Interface      #
#  - platform class                      #
##########################################

class KhBase(object):
  def __init__(self):
    None
  
  # cli parser methods
  def parse_clean(self):
    None
  def parse_get(self):
    None
  def parser_init(self):
    None
  def parser_install(self):
    None
  def parser_rm(self):
    None
  def parser_setup(self):
    None

  # kh methods
  def clean(self):
    None
  def get(self):
    None
  def info(self):
    None
  def install(self):
    None
  def rm(self):
    None
  def setup(self):
    None

  # misc
  def test(self):
    print "You found base!"
