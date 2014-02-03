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
import daemon
import lockfile
import sys
import signal

from SimpleXMLRPCServer import SimpleXMLRPCServer
import xmlrpclib


class KhServerConfig(object):
  def __init__(self, server_ip, server_port, pidfile_path, stdin_path,
      stdout_path, stderr_path):
    self.server_ip = server_ip
    self.server_port = server_port
    touch(pidfile_path)
    self.pidfile_path = pidfile_path
    touch(stdin_path)
    self.stdin_path = stdin_path
    touch(stdout_path)
    self.stdout_path = stdout_path
    touch(stderr_path)
    self.stderr_path = stderr_path

# Kittyhawk root server object
class KhServer(object):

  #''' local filesystem database '''
  #def get_dbpath():
  #  cval = Config.get('global', 'db')
  #  sval = os.getenv('KHDB')
  #  dbpath = ""
  #  # explicit config setting trumps any envoirment variables
  #  if len(cval) > 0:
  #    dbpath = cval
  #  elif sval != None:
  #    dbpath = sval
  #  # verify path
  #  if os.path.exists(dbpath) == 0:
  #    print "Error: invalid db path ", dbpath
  #    exit()
  #  else:
  #    return dbpath

  def __init__(self, configsrc):
    self.config = ConfigParser.SafeConfigParser()
    configsrc.append("khdb.cfg")
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
    # deamon
    self.daemon_context = daemon.DaemonContext()
    

  # Default command parsers ##########################################

  def add_parsers(self, subpar):
    # clean
    self.parse_clean(subpar.add_parser('clean',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
      description="Remove network, reset nodes"))
    # info
    self.parse_info(subpar.add_parser('info',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
      description="List all networks and nodes"))
    # install
    self.parse_install(subpar.add_parser('install',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
      description="Install Kittyhawk database "))
    # restart
    self.parse_restart(subpar.add_parser('restart',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
      description="Reboot server"))
    # start
    self.parse_start(subpar.add_parser('start',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
      description="Bring server online. Initialize freepool"))
    # stop
    self.parse_stop(subpar.add_parser('stop',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
      description="Take server offline"))
    
  def parse_clean(self, parser):
    parser.set_defaults(func=self.clean)
    return parser

  def parse_info(self, parser):
    parser.set_defaults(func=self.info)
    return parser

  def parse_install(self, parser):
    parser.set_defaults(func=self.install)
    return parser

  def parse_restart(self, parser):
    parser.set_defaults(func=self.restart)
    return parser

  def parse_start(self, parser):
    parser.set_defaults(func=self.start)
    return parser

  def parse_stop(self, parser):
    parser.set_defaults(func=self.stop)
    return parser



  # Default actions ####################################################

  def alloc_client(self, jobid, count):
    ''' Allocate a Node on a Network. Called through client interface '''
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


  def clean(self):
    ''' Clean all nodes and networks '''
    ''' remove node files '''
    self.db_node_rm('*','*','*')
    self.db_job_rm('*','*')
    ''' remove job data subdirectories '''
    datapath = os.path.join(self.db_path,
        self.config.get("BaseDirectories", "jobdata"))
    shutil.rmtree(datapath)
    os.mkdir(datapath)

  def clean_client(self):
    ''' Clean all Nodes and Networks for a particular user '''
    return "Not yet supported"


  def console_client(self, key):
    ''' Console stream to a node '''
    print "Console support is not yet available."


  def info(self):
    ''' Display all network information '''
    # list each app and the number of nodes
    for file in os.listdir(self.data_job_path):
      job = file[0:file.find(':')]
      jobid = file[file.find(':')+1:len(file)]
      nodes = self.db_node_get('*',job,jobid)
      print job, jobid, len(nodes)

  def info_client(self):
    ''' Display all network information for a particualr user'''
    return "Not yet supported"

  def init(self, count=0):
    ''' Initilaize kittyhawk playform
    
        Reset counts to default. Free all nodes
    '''
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
    ''' Install empty framework '''
    # create db directories (if needed)
    for s in self.config.options("BaseDirectories"):
      d = self.config.get("BaseDirectories", s)
      if os.path.exists(os.path.join(self.db_path, d)) == 0:
        os.mkdir(os.path.join(self.db_path, d))
    # create db files (if needed)
    for s in self.config.options("BaseFiles"):
      d = self.config.get("BaseFiles", s)
      if os.path.exists(os.path.join(self.db_path, d)) == 0:
        touch(os.path.join(self.db_path, d))


  def network_client(self):
    ''' Allocate a network '''
   # for file in os.listdir(self.data_job_path):
   #   if fnmatch.fnmatch(file, job+":*"):
   #     print "Error: network '"+job+"' already exists"
   #     return None
    # make directory
    jid =  self.db_job_set() 
    if os.path.exists(os.path.join(self.netpath, str(jid))) == 0:
        os.mkdir(os.path.join(self.netpath, str(jid)))
    return jid


  def remove(self, job):
    ''' Remove a network, free connected nodes '''
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

  def remove_client(self, job):
    ''' Remove a network, free nodes. Client validation '''
    return "Not yet implemented"

  def restart(self):
    ''' Restart the server'''
    self.stop()
    self.start()
    return 0

  def server_config(self):
    ''' Server config must be defined in child class '''
    self._print("Error: no server configuration found")
    exit(1)
    return 0

  def start(self):
    ''' Bring server online '''
    self.init(); # reset server defaults, free all nodes
    config = self.server_config()
    
    # aquire lock on pidfile
    lock = lockfile.FileLock(config.pidfile_path)
    while not lock.i_am_locking():
      try:
        lock.acquire(timeout=3)  # wait up to 60 seconds
      except lockfile.LockTimeout:
        print "pidfile is locked. Try stopping the server"
        exit(1)

    self.daemon_context.stdin = open(config.stdin_path, 'r')
    self.daemon_context.stdout = open(config.stdout_path, 'w+')
    self.daemon_context.stderr = open(config.stderr_path, 'w+', buffering=0)
    self.daemon_context.open()
    # running as daemon
    with open(config.pidfile_path, "a") as f:
      f.seek(0)
      f.truncate()
      f.write(str(os.getpid()))
    
    server = SimpleXMLRPCServer((config.server_ip, int(config.server_port)))
    server.register_function(self.alloc_client,   "alloc")
    server.register_function(self.console_client, "console")
    server.register_function(self.network_client, "network")
    server.register_function(self.clean_client,   "clean")
    server.register_function(self.info_client,    "info")
    server.register_function(self.remove_client,  "remove")
    self._print("Listening on "+config.server_ip+":"+str(config.server_port))
    server.serve_forever()

  ''' Bring server offline '''
  def stop(self):
    config = self.server_config()
    lock = lockfile.FileLock(config.pidfile_path)
    while not lock.i_am_locking():
      try:
        lock.acquire(timeout=5)  # wait up to 60 seconds
      except lockfile.LockTimeout:
        lock.break_lock()
        pid=int(next(open(config.pidfile_path)))
        self._print("Shutting down service, pid="+str(pid))
        lock.break_lock()
        os.kill(pid, signal.SIGKILL)
        with open(config.pidfile_path, "a") as f:
          f.seek(0)
          f.truncate()
        exit(1)
    print "Server is not online"


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
    #touch(rpath)
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
    touch(fnew)
  
  # utility methods #############################################

  def _print(self, message, stream=None):
      """ Emit a message to the specified stream (default `sys.stderr`). """
      if stream is None:
        stream = sys.stderr
      stream.write("%(message)s\n" % vars())
      stream.flush()

def touch(fname, times=None):
  '''  safely create an empty file '''
  if os.path.isfile(fname) == False:
    with file(fname, 'a'):
      os.utime(fname, times)
