##########################################
#  Kittyhawk Command-line Interface      #
#  - platform class                      #
##########################################

class KhBase(object):
  def __init__(self):
    None
  
  # cli parser methods
  def clean_parser(self):
    None
  def get_parser(self):
    None
  def info_parser(self):
    None
  def install_parser(self):
    None
  def rm_parser(self):
    None
  def setup_parser(self):
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
