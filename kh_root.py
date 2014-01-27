##########################################
#  Kittyhawk Command-line Interface      #
#  - root platform class                 #
##########################################

import argparse
import ConfigParser 
import copy 
import fnmatch
import os
import shutil
import subprocess

def _ensure_value(namespace, name, value):
    if getattr(namespace, name, None) is None:
        setattr(namespace, name, value)
    return getattr(namespace, name)

# our custom parameterizers
class KH_store_required(argparse.Action):
  def __call__(self, parser, namespace, values, option_string=None):
    items = copy.copy(_ensure_value(namespace, 'required_args', []))
    items.append(self.dest)
    setattr(namespace, 'required_args', items)
    setattr(namespace, self.dest, values)

class KH_store_optional_const(argparse._StoreConstAction):
  def __call__(self, parser, namespace, values, option_string=None):
    items = copy.copy(_ensure_value(namespace, 'optional_args', {}))
    items[self.dest] = self.const
    setattr(namespace, 'optional_args', items)
    
class KH_store_optional(argparse._StoreAction):
  def __call__(self, parser, namespace, values, option_string=None):
    items = copy.copy(_ensure_value(namespace, 'optional_args', {}))
    items[self.dest] = values
    setattr(namespace, 'optional_args', items)

# Kittyhawk root object
class KhRoot(object):
  def __init__(self, configsrc, dbpath):
    self.config = ConfigParser.SafeConfigParser()
    self.config.read(configsrc)
    self.db_path = dbpath
    self.data_node_path = os.path.join(self.db_path,
        self.config.get("BaseDirectories","nodes"))
    self.data_network_path = os.path.join(self.db_path,
        self.config.get("BaseDirectories","network"))
    self.data_job_path = os.path.join(self.db_path,
        self.config.get("BaseDirectories","job"))

  # Default command parsers ##########################################

  def parse_alloc(self, parser):
    parser.set_defaults(func=self.alloc)
    parser.add_argument('job',type=str,action=KH_store_required, 
      help="Name of user")
    parser.add_argument('count',type=int,action=KH_store_required, 
      help="Amount of instances")
    return parser

  def parse_clean(self, parser):
    parser.set_defaults(func=self.clean)
    return parser

  def parse_console(self, parser):
    parser.add_argument('key',action=KH_store_required,
      help="Instance identifier")
    parser.set_defaults(func=self.console)
    return parser

  def parse_info(self, parser):
    parser.set_defaults(func=self.info)
    return parser

  def parse_install(self, parser):
    parser.set_defaults(func=self.install)
    return parser

  def parse_network(self, parser):
    parser.add_argument('job', action=KH_store_required,
      help="Name of network")
    parser.set_defaults(func=self.network)
    return parser

  def parse_remove(self, parser):
    # TODO: allow '*' and User1, User2...
    parser.add_argument('job', action=KH_store_required,
      help="Name of network")
    parser.set_defaults(func=self.remove)
    return parser

  def parse_init(self, parser):
    parser.set_defaults(func=self.init)
    return parser

  # Default actions ####################################################

  def alloc(self, job, count):
    ''' 
    Input: job name, instance count
    Output: node cookies
    '''
    #check if job record exists
    jobid = None
    for file in os.listdir(self.data_job_path):
      if fnmatch.fnmatch(file, job+":*"):
        jobid = str(file).split(':')[1];
        break
    if jobid == None: 
      print "Error: network not found"
      exit(1) 
      #jobid = self.db_job_set(job) 
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


  def clean(self):
    ''' remove node files '''
    self.db_node_rm('*','*','*')
    self.db_job_rm('*','*')
    ''' remove job data subdirectories '''
    datapath = os.path.join(self.db_path,
        self.config.get("BaseDirectories", "jobdata"))
    shutil.rmtree(datapath)
    os.mkdir(datapath)


  def console(self, key):
    print "Console support is not available."


  def info(self):
    # list each app and the number of nodes
    for file in os.listdir(self.data_job_path):
      job = file[0:file.find(':')]
      jobid = file[file.find(':')+1:len(file)]
      nodes = self.db_node_get('*',job,jobid)
      print job, jobid, len(nodes)


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


  def network(self, job):
    for file in os.listdir(self.data_job_path):
      if fnmatch.fnmatch(file, job+":*"):
        print "Error: network '"+job+"' already exists"
        exit(1) 
    # make directory
    jid =  self.db_job_set(job) 
    if os.path.exists(os.path.join(self.job_path, str(jid))) == 0:
        os.mkdir(os.path.join(self.job_path, str(jid)))
    return jid


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




  # database methods ################################################

  # return filename of first matching job record
  def db_job_get(self, job, jobid):
    f = str(job)+":"+str(jobid)
    for file in os.listdir(self.data_job_path):
      if fnmatch.fnmatch(file, f):
        return file
    return None

  # Grab next jobid and assign it to job
  def db_job_set(self, job): 
    rid=int(next(open(self.db_path+'/'+self.config.get('BaseFiles','jobid'))))
    nextid=rid+1
    # increase jobid count
    with open(self.db_path+'/'+self.config.get('BaseFiles', 'jobid'), "a") as f:
      f.seek(0)
      f.truncate()
      f.write(str(nextid))
    # setup db record
    rpath = self.db_path+'/'+self.config.get('BaseDirectories','job')+\
      '/'+str(job)+':'+str(rid)
    self.touch(rpath)
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
  
  # Defauly utility functions #############################################

  # safely create an empty file
  def touch(self, fname, times=None):
    with file(fname, 'a'):
      os.utime(fname, times)

