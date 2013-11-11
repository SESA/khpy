##########################################
#  Kittyhawk Command-line Interface      #
#  - base platform class                 #
##########################################

from __future__ import print_function
import argparse
import ConfigParser 
import copy 
import fnmatch
import os
import subprocess

def _ensure_value(namespace, name, value):
    if getattr(namespace, name, None) is None:
        setattr(namespace, name, value)
    return getattr(namespace, name)

# our custom parameterizer
class Parameterize(argparse.Action):
  def __call__(self, parser, namespace, values, option_string=None):
    items = copy.copy(_ensure_value(namespace, self.metavar, []))
    items.append(self.dest)
    setattr(namespace, self.metavar, items)
    setattr(namespace, self.dest, values)
    

class KhBase(object):
  def __init__(self, configsrc):
    self.config = ConfigParser.SafeConfigParser()
    self.config.read(configsrc)
    self.db_path = os.getenv("KHDB")
    self.data_node_path = os.path.join(self.db_path,
        self.config.get("BaseDirectories","nodes"))
    self.data_network_path = os.path.join(self.db_path,
        self.config.get("BaseDirectories","network"))
    self.data_user_path = os.path.join(self.db_path,
        self.config.get("BaseDirectories","user"))

  # cli parser methods   ################################################

  def parse_clean(self, parser):
    parser.set_defaults(func=self.clean)
    return parser

  def parse_get(self, parser):
    parser.set_defaults(func=self.get)
    parser.add_argument('job', action=Parameterize, metavar="arg")
    parser.add_argument('count', action=Parameterize, metavar="arg")
    return parser

  def parse_info(self, parser):
    parser.set_defaults(func=self.info)
    return parser

  def parse_install(self, parser):
    parser.set_defaults(func=self.install)
    return parser

  def parse_rm(self, parser):
    parser.set_defaults(func=self.rm)
    return parser

  def parse_setup(self, parser):
    parser.set_defaults(func=self.setup)
    return parser

  # action methods ####################################################

  def clean(self):
    print("base clean")
    '''
        remove node files
        clear node counts
    '''

  def get(self, job, count):
    ''' 
    Input: jobname, none-count
    Process:
        - check if job record exists
           if not, make job record, set conid, netid
        - get and set next free node record
        - 
    '''
    print("get -->", job, count)

  def info(self):
    print ("base info")

  def install(self):
    # create db directories (if needed)
    for s in self.config.options("BaseDirectories"):
      d = self.config.get("BaseDirectories", s)
      if os.path.exists(os.path.join(self.db_path, d)) == 0:
        os.mkdir(os.path.join(self.db_path, d))
    # create db files (if needed)
    for s in self.config.options("BaseFiles"):
      d = self.config.get("BaseFiles", s)
      if os.path.exists(os.path.join(self.db_path, d)) == 0:
        cmd = ["touch", os.path.join(self.db_path, d)]
        subprocess.call(cmd)

  def rm(self):
    '''
    Input: jobname
    Process: 
      - from job record grab conid, remove job record
      - from conid, node list
      - remove node records, node list
    '''
    print( "Warning: base rm does nothing")

  def setup(self, count=0):
    '''
    Input: max instance count (optional)
    Process: 
    '''
    # TODO: run clean initially  
    if count == 0:
      count=self.config.getint("Defaults", "instance_count")
    # set record for each node 
    for i in range(count):
      self.db_node_set(i, self.config.get('Settings','FreeOwner'),
          self.config.get('Settings','FreeConID'))
    # set ids to default  
    for s in self.config.options("BaseFiles"):
      d = self.config.get("BaseFiles", s)
      if os.path.isfile(os.path.join(self.db_path, d)) == 1:
        f = open(self.db_path+'/'+self.config.get('BaseFiles', s), 'w')
        print(self.config.get('Defaults',s), file=f)
        f.close()



  # database methods ################################################

  ''' TODO
    - method to remove a list of nodes 

  '''

  # remove matching record(s)
  def db_node_rm(self, node, owner, conid):
    f = str(node)+":"+str(owner)+":"+str(conid)
    for file in os.listdir(self.data_node_path):
        if fnmatch.fnmatch(file, f):
            os.remove(self.data_node_path+"/"+file)

  # create new record
  def db_node_set(self, node, owner, conid):
    self.db_node_rm(str(node), "*", "*")
    fnew = self.data_node_path+ "/"+str(node)+":"+str(owner)+":"+str(conid)
    self.touch(fnew)

  # utility functions ################################################

  # create empty file
  def touch(self, fname, times=None):
    with file(fname, 'a'):
      os.utime(fname, times)

  def test(self):
    print( "You found base!")
