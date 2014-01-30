##########################################
#  Kittyhawk Command-line Interface      #
#  - root platform class                 #
##########################################

from kh_shared import *
import argparse
import ConfigParser 
import copy 
import fnmatch
import os
import shutil
import subprocess

from SimpleXMLRPCServer import SimpleXMLRPCServer
import xmlrpclib

# Kittyhawk root server object
class KhServer(object):

  ''' local filesystem database '''
  def get_dbpath():
    cval = Config.get('global', 'db')
    sval = os.getenv('KHDB')
    dbpath = ""
    # explicit config setting trumps any envoirment variables
    if len(cval) > 0:
      dbpath = cval
    elif sval != None:
      dbpath = sval
    # verify path
    if os.path.exists(dbpath) == 0:
      print "Error: invalid db path ", dbpath
      exit()
    else:
      return dbpath

  def __init__(self, configsrc):
    self.config = ConfigParser.SafeConfigParser()
    self.config.read(configsrc)
    self.db_path = self.config.get("database","path")
    self.netpath = os.path.join(self.db_path,
        self.config.get("BaseDirectories","jobdata"))
    self.data_node_path = os.path.join(self.db_path,
        self.config.get("BaseDirectories","nodes"))
    self.data_network_path = os.path.join(self.db_path,
        self.config.get("BaseDirectories","network"))
    self.data_job_path = os.path.join(self.db_path,
        self.config.get("BaseDirectories","job"))

  # Default command parsers ##########################################

  def parse_extras(self, subpar):
    # install
    self.parse_install(subpar.add_parser('install',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
      description="Install Kittyhawk database "))
    # up
    self.parse_up(subpar.add_parser('up',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
      description="Bring server online. Initialize freepool"))
    # down
    self.parse_down(subpar.add_parser('down',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
      description="Take server offline"))
    
  def parse_install(self, parser):
    parser.set_defaults(func=self.install)
    return parser

  def parse_down(self, parser):
    parser.set_defaults(func=self.down)
    return parser

  def parse_up(self, parser):
    parser.set_defaults(func=self.up)
    return parser

  ''' below this line are shared commands '''

  def parse_clean(self, parser):
    parser.set_defaults(func=self.clean)
    return parser

  def parse_info(self, parser):
    parser.set_defaults(func=self.info)
    return parser

  # Default actions ####################################################

  ''' Allocate a Node on a Network. Called through client interface '''
  def alloc_client(self, jobid, count):
    #TODO verify network
    #if jobid == None: 
    #  print "Error: network not found"
    #  exit(1) 
    # create data directory
    datapath = os.path.join(self.db_path,
        self.config.get("BaseDirectories", "jobdata")+'/'+str(jobid))
    if os.path.exists(datapath) == 0:
      os.mkdir(datapath)
    # get node id
    nodes = self.db_node_get('*',self.config.get('Settings','FreeOwner'),
        '*',count)
    # this check should be somewhere smarter..
    if len(nodes) == 0:
      print "Error: not enough free nodes available"
      exit(1)
    # assign nodes
    gotlist = []
    for node in nodes:
      nid = node[0:node.find(':')]
      gotlist.append(nid)
      self.db_node_set(nid, job, jobid)
      if os.path.exists(datapath+'/'+str(nid)) == 0:
        os.mkdir(datapath+'/'+str(nid))
    return gotlist


  ''' Clean all Nodes and Networks '''
  def clean(self):
    ''' remove node files '''
    self.db_node_rm('*','*','*')
    self.db_job_rm('*','*')
    ''' remove job data subdirectories '''
    datapath = os.path.join(self.db_path,
        self.config.get("BaseDirectories", "jobdata"))
    shutil.rmtree(datapath)
    os.mkdir(datapath)

  ''' Clean all Nodes and Networks for a particular user '''
  def clean_client(self):
    return "Not yet supported"


  ''' Console stream to a node '''
  def console_client(self, key):
    print "Console support is not available."


  ''' Display all network information '''
  def info(self):
    # list each app and the number of nodes
    for file in os.listdir(self.data_job_path):
      job = file[0:file.find(':')]
      jobid = file[file.find(':')+1:len(file)]
      nodes = self.db_node_get('*',job,jobid)
      print job, jobid, len(nodes)

  ''' Display all network information for a particualr user'''
  def info_client(self):
    return "Not yet supported"


  ''' Initilaize playform '''
  def init(self, count=0):
    self.clean()
    if count == 0:
      count=self.config.getint("Defaults", "instance_count")
    # set record for each node 
    for i in range(count):
      self.db_node_set(i, self.config.get('Settings','FreeOwner'),
          self.config.get('Settings','FreeJobID'))
    # set ids to default  
    for s in self.config.options("BaseFiles"):
      d = self.config.get("BaseFiles", s)
      if os.path.isfile(os.path.join(self.db_path, d)) == 1:
        with open(self.db_path+'/'+self.config.get('BaseFiles', s), "a") as f:
          f.seek(0)
          f.truncate()
          f.write(self.config.get('Defaults',s))
    print "Setup complete."


  ''' Install playform '''
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
        self.touch(os.path.join(self.db_path, d))


  ''' Allocate a network '''
  def network_client(self):
   # for file in os.listdir(self.data_job_path):
   #   if fnmatch.fnmatch(file, job+":*"):
   #     print "Error: network '"+job+"' already exists"
   #     return None
    # make directory
    jid =  self.db_job_set() 
    if os.path.exists(os.path.join(self.netpath, str(jid))) == 0:
        os.mkdir(os.path.join(self.netpath, str(jid)))
    return jid


  ''' Remove a network, free nodes '''
  def remove(self, job):
    record = self.db_job_get(job, '*')
    if record == None:
      print "Error: no job record found"
      exit(1)
    jobid = record[record.find(':')+1:len(record)]
    self.db_job_rm(job, jobid)
    nodes = self.db_node_get('*', job, jobid)
    # set nodes as free
    for node in nodes:
      nid = node[0:node.find(':')]
      self.db_node_set(nid,
          self.config.get('Settings','FreeOwner'),self.config.get('Settings',
            'FreeJobID'))
    # remove job data directories
    datapath = os.path.join(self.db_path,
        self.config.get("BaseDirectories", "jobdata")+'/'+str(jobid))
    if os.path.exists(datapath) == 1:
      shutil.rmtree(datapath)

  ''' Remove a network, free nodes. Client validation '''
  def remove_client(self, job):
    return "Not yet implemented"


  ''' Bring server online '''
  def up(self):
    self.init();
    server = SimpleXMLRPCServer(("localhost", 8000))
    server.register_function(self.alloc_client)
    server.register_function(self.console_client)
    server.register_function(self.network_client)
    server.register_function(self.clean_client, "clean")
    server.register_function(self.info_client, "info")
    server.register_function(self.remove_client, "remove")
    print "Listening on localhost port 8000..."
    server.serve_forever()

  ''' Bring server offline '''
  def down(self):
    print "Server offline"


  # database methods ################################################

  # return filename of first matching job record
  def db_job_get(self, job, jobid):
    f = str(job)+":"+str(jobid)
    for file in os.listdir(self.data_job_path):
      if fnmatch.fnmatch(file, f):
        return file
    return None

  # Grab next jobid and assign it to job
  def db_job_set(self): 
    rid=int(next(open(self.db_path+'/'+self.config.get('BaseFiles','jobid'))))
    nextid=rid+1
    # increase jobid count
    with open(self.db_path+'/'+self.config.get('BaseFiles', 'jobid'), "a") as f:
      f.seek(0)
      f.truncate()
      f.write(str(nextid))
    # setup db record
    #rpath = self.db_path+'/'+self.config.get('BaseDirectories','job')+\
    #  '/'+str(job)+':'+str(rid)
    #self.touch(rpath)
    return rid

  # remove DB record, return (expired) jobid
  def db_job_rm(self, job, jobid):
    f = str(job)+":"+str(jobid)
    for file in os.listdir(self.data_job_path):
      if fnmatch.fnmatch(file, f):
        os.remove(self.data_job_path+"/"+file)
    return jobid

  # return matching node record(s)
  def db_node_get(self, node, job, conid, count=None):
    f = str(node)+":"+str(job)+":"+str(conid)
    retlist=[]
    for file in os.listdir(self.data_node_path):
      if fnmatch.fnmatch(file, f):
        retlist.append(file)
        if count != None and len(retlist) == count:
          break
    return retlist

  # delete matching node record(s)
  def db_node_rm(self, node, job, conid):
    f = str(node)+":"+str(job)+":"+str(conid)
    for file in os.listdir(self.data_node_path):
        if fnmatch.fnmatch(file, f):
            os.remove(self.data_node_path+"/"+file)

  # create new node record
  def db_node_set(self, node, job, conid):
    self.db_node_rm(str(node), "*", "*")
    fnew = self.data_node_path+ "/"+str(node)+":"+str(job)+":"+str(conid)
    self.touch(fnew)
  


  # utility methods #############################################

  # safely create an empty file
  def touch(self, fname, times=None):
    with file(fname, 'a'):
      os.utime(fname, times)

