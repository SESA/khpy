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
import sys
import signal
import xmlrpclib
from SimpleXMLRPCServer import SimpleXMLRPCServer
from kh_shared import *
import lockfile

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
  def __init__(self, configsrc):
    self.config = ConfigParser.SafeConfigParser()
    khsrc = os.path.dirname(os.path.abspath(__file__))
    dbconfigfile = os.path.join(khsrc,"khdb.cfg")
    configsrc.append(dbconfigfile)
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
    # debug info
    self.debug = self.config.get("debug","debug")

  # Default command parsers ##########################################

  def add_parsers(self, subpar):
    # clean
    self.parse_clean(subpar.add_parser('clean',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
      description="Stop server and delete database"))
    # info
    self.parse_info(subpar.add_parser('info',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
      description="List networks and nodes"))
    # install
    self.parse_install(subpar.add_parser('install',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
      description="Install database"))
    # reinstall
    self.parse_install(subpar.add_parser('reinstall',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
      description="Stop server, delete and reinstall database, relaunch server"))
    # restart
    self.parse_restart(subpar.add_parser('restart',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
      description="Restart khpy server"))
    # start
    self.parse_start(subpar.add_parser('start',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
      description="Start khpy server "))
    # stop
    self.parse_stop(subpar.add_parser('stop',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
      description="Stop khpy server daemon (if found)"))
    
  def parse_clean(self, parser):
    parser.set_defaults(func=self.clean)
    return parser

  def parse_info(self, parser):
    parser.set_defaults(func=self.info)
    return parser

  def parse_install(self, parser):
    parser.set_defaults(func=self.install)
    return parser

  def parse_reinstall(self, parser):
    parser.add_argument('-D', 
            action=KH_store_optional_const, 
            const=1,
            help='Start daemon ( req:python-daemon )')
    parser.set_defaults(func=self.reinstall)
    return parser

  def parse_restart(self, parser):
    parser.add_argument('-D', 
            action=KH_store_optional_const, 
            const=1,
            help='Restart daemon ( req:python-daemon )')
    parser.set_defaults(func=self.restart)
    return parser

  def parse_start(self, parser):
    parser.add_argument('-D', 
            action=KH_store_optional_const, 
            const=1,
            help='Start daemon ( req:python-daemon )')
    parser.set_defaults(func=self.start)
    return parser

  def parse_stop(self, parser):
    parser.set_defaults(func=self.stop)
    return parser

  # Client actions ####################################################
  #     these methods are called remotely and should -eventually- contain
  #     verification

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
    nodes = self.db_node_get('*',self.config.get('Settings','FreeJobID'),
        count)
    # this check should be somewhere smarter..
    if len(nodes) == 0:
      print "Error: not enough free nodes available"
      exit(1)
    # assign nodes
    gotlist = []
    print "Allocating nodes: ",nodes
    for node in nodes:
      nid = node[0:node.find(':')]
      gotlist.append(nid)
      self.db_node_set(nid, jobid)
      if os.path.exists(datapath+'/'+str(nid)) == 0:
        os.mkdir(datapath+'/'+str(nid))
    return gotlist


  def clean_client(self,uid):
    ''' Clean all Nodes and Networks for a particular user '''
    nets = self.db_net_listbyuid(uid)
    for name in nets:
      self.remove_network(name)
    return "Your networks and nodes have been removed"


  def console_client(self, key):
    ''' Console stream to a node '''
    print "Console support is not yet available."


  def info_client(self):
    ''' Display all network information for a particualr user'''
    return "Not yet supported"


  def network_client(self,uid):
    ''' Allocate a network '''
    jid =  self.db_net_set()
    net_path = os.path.join(self.netpath, str(jid))
    net_uid_path = os.path.join(net_path, "uid")
    if os.path.exists(net_path) == 0:
        os.mkdir(net_path)
        touch(net_uid_path)
        with open(net_uid_path, "a") as f:
          f.seek(0)
          f.truncate()
          f.write(str(uid))
    else:
      self._print("Error: network "+str(jid)+" already allocated")
    self._print("Allocating network #"+str(jid), sys.stdout)
    return jid

  def remove_node_client(self, node):
    ''' Free a node. Client validation '''
    ## TODO: some sort of user validation
    return self.remove_node(node)


  def remove_network_client(self, network):
    ''' Remove a network, free nodes. Client validation '''
    ## TODO: some sort of user validation
    return self.remove_network(network)

  # Server actions ####################################################
  # these methods are called directly from the CLI 
  #

  def clean(self):
    ''' Clean all nodes and networks '''
    print "Cleaning up service..."
    if self.server_is_online() == True:
      self.stop()

    nets = self.db_net_list()
    for name in nets:
      self.remove_network(name)

    # reset node records
    self.db_node_rm('*','*')
    # remove all nets
    npath = os.path.join(self.netpath)
    if os.path.isdir(npath):
        shutil.rmtree(npath) # delete directory tree!
    # remove job data subdirectories
    datapath = os.path.join(self.db_path,
        self.config.get("BaseDirectories", "jobdata"))
    if os.path.isdir(datapath):
        shutil.rmtree(datapath)
    os.mkdir(datapath)

  def init(self, count=0, start=0):
    ''' Initilaize the Kittyhawk playform
        Reset counts to default. Reset node and network records
    '''
    if count == 0:
      count=self.config.getint("Defaults", "instance_max")
    # set record for each node
    for i in range(start,start+count):
      self.db_node_set(i, self.config.get('Settings','FreeJobID'))
    print "Setup complete."

  def install(self):
    ''' Install empty Kittyhawk framework 
        Creates the directories and files nessessary to initialize
        and start the Kittyhawk server
    '''
    # create db directories (if needed)
    print self.db_path
    if os.path.exists(self.db_path) == 0:
      os.mkdir(self.db_path)
      print self.db_path
    for s in self.config.options("BaseDirectories"):
      d = self.config.get("BaseDirectories", s)
      if os.path.exists(os.path.join(self.db_path, d)) == 0:
        os.mkdir(os.path.join(self.db_path, d))
    # create db files (if needed)
    for s in self.config.options("BaseFiles"):
      d = self.config.get("BaseFiles", s)
      if os.path.exists(os.path.join(self.db_path, d)) == 0:
        touch(os.path.join(self.db_path, d))
        with open(self.db_path+'/'+self.config.get('BaseFiles', s), "a") as f:
          f.seek(0)
          f.truncate()
          f.write(self.config.get('Defaults',s))
    with open(self.db_path+'/'+self.config.get("BaseFiles","nodeid") ,"r+") as f:
        start=f.read()
        f.seek(0)
        f.truncate()
        f.write(str(int(start)+128))
    self.init(0,int(start))
    print "Initialization complete. Ready to start "

  def reinstall(self, option={}):
      self.stop()
      self.clean()
      self.install()
      self.start(option)

  def remove_node(self, node, netid=None):
    ''' Remove a paticular node from a network '''
    if netid is None:
      nodes = self.db_node_get(node, '*')
      noderec = nodes[0]
      if noderec is not None:
        netid = noderec[noderec.find(':')+1:len(noderec)]
      else:
        self._print("Warning: no network for node #"+str(node))
        return 0
    # remove node directory
    datapath = os.path.join(os.path.join(self.db_path,
               self.config.get("BaseDirectories", "jobdata")),str(netid))
    nodedatapath = os.path.join(datapath, str(node))
    if os.path.exists(nodedatapath) == 1:
      shutil.rmtree(nodedatapath)
    self.db_node_set(node, self.config.get('Settings', 'FreeJobID'))
    print "Removed node "+str(node)+" from network "+str(netid)
    return "Removed node "+str(node)+" from network "+str(netid)


  def remove_network(self, netid):
    ''' Remove a network, free connected nodes

        This method will reset the network and nodes records and
        delete the network directory. Make sure you are finished
        with all data within the network directory (e.g, pidfiles)
    '''
    nodes = self.db_node_get('*', netid)
    # set nodes as free
    for node in nodes:
      nid = node[0:node.find(':')]
      self.db_node_set(nid, self.config.get('Settings', 'FreeJobID'))
    # remove net data directories
    datapath = os.path.join(os.path.join(self.db_path,
        self.config.get("BaseDirectories", "jobdata")),str(netid))
    if os.path.exists(datapath) == 1:
      shutil.rmtree(datapath)
    print "Removing network:",str(netid)
    return "Network "+str(netid)+" removed"

  def info(self):
    ''' Display all network information '''
    #list each app and the number of nodes
    for file in os.listdir(self.data_job_path):
      job = file[0:file.find(':')]
      jobid = file[file.find(':')+1:len(file)]
      nodes = self.db_node_get('*',jobid)
      print job, jobid, len(nodes)

  def restart(self, option={}):
    ''' Stop and resume the server 
        Previous state is kept intact (use 'clean' otherwise)
    '''
    self.stop()
    self.start(option)
    return 0

  def server_config(self):
    ''' Server settings must be defined in child class '''
    self._print("Error: child class must contain server_config() function")
    exit(1)
    return 0

  def start(self, option={}):
    ''' Bring server online

        By default, the server will resume its pervious state, presuming other
        processes are still runningi externally. Optionally, this function
        should check if the server had not previous initialized and do so.
    '''
    config = self.server_config()
    daemon = False
    if option.has_key('D') and option['D'] is 1:
        daemon = True
    print "Starting server..."
    if daemon:
      # aquire lock on pidfile
      lock = lockfile.FileLock(config.pidfile_path)
      while not lock.i_am_locking():
        try:
          lock.acquire(timeout=3)  # wait up to 3 seconds
        except lockfile.LockTimeout:
          print "Server is already running"
          exit(1)
      print "Laching daemon..."
      try:
        import daemon
      except ImportError:
        print "Error: python daemon module is not found. Run with -D to disable daemon"
        self.stop()
        exit(1)
      self.daemon_context = daemon.DaemonContext()
      self.daemon_context.stdin = open(config.stdin_path, 'r')
      self.daemon_context.stdout = open(config.stdout_path, 'w+')
      self.daemon_context.stderr = open(config.stderr_path, 'w+', buffering=0)
      self.daemon_context.open()
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
    server.register_function(self.remove_network_client,"remove_network")
    server.register_function(self.remove_node_client,"remove_node")
    self._print("Listening on "+config.server_ip+":"+str(config.server_port))
    server.serve_forever()

  def stop(self):
    ''' Take server offline '''
    config = self.server_config()
    lock = lockfile.FileLock(config.pidfile_path)
    print "Shutting down server..."
    while not lock.i_am_locking():
      try:
        lock.acquire(timeout=3)  # wait up to 3 seconds
      except lockfile.LockTimeout:
        lock.break_lock()
        if os.path.isfile(config.pidfile_path) == True:
          try:
            pid=int(next(open(config.pidfile_path)))
            self._print("removing server process, pid="+str(pid))
            try:
              os.kill(pid, signal.SIGKILL)
            except OSError:
              self._print("No process to kill. ")
          except StopIteration:
            self._print("No server process found")
          with open(config.pidfile_path, "a") as f:
            f.seek(0)
            f.truncate()
          return 0
    lock.break_lock()
    print "Timeout: Server is not online"


  # validation  ##########################################################
  #

  def node_is_valid(self, node):
    ''' Verify that a node is allocated

        Return True/False
    '''
    pull = self.db_node_get(node,'*')
    if len(pull) is 1:
      noderec = pull[0]
      netid = noderec[noderec.find(':')+1:len(noderec)]
      # verify node is assigned to a network
      if netid is not self.config.get('Settings','FreeJobID'):
        return True
    return False # no valid node record

  def server_is_online(self):
    config = self.server_config()
    lock = lockfile.FileLock(config.pidfile_path)
    while not lock.i_am_locking():
      try:
        lock.acquire(timeout=3)  # wait up to 3 seconds
      except lockfile.LockTimeout:
        lock.break_lock()
        # lock is held by running server
        return True
    # able to aquire lock, server is offline
    lock.break_lock()
    return False

  def network_is_valid(self, net):
    ''' Verify that a network is active
        Return True/False
    '''
    if self.db_net_get(net) is None:
      return False
    else:
      return True # we may want some additional validation here...


  # database control ##########################################################

  #  Network methods
  def db_net_set(self): 
    ''' Grab next netid, increment count 
        Always returns int
    '''
    rid=int(next(open(self.db_path+'/'+self.config.get('BaseFiles','jobid'))))
    nextid=rid+1
    # increase jobid count
    with open(self.db_path+'/'+self.config.get('BaseFiles', 'jobid'), "a") as f:
      f.seek(0)
      f.truncate()
      f.write(str(nextid))
    return rid

  def db_net_rm(self, net):
    ''' Remove network directory, return (expired) jobid

        Only run this once you are done with all the files within!
    '''
    path = self.db_net_get(net)
    if not (path is None):
        shutil.rmtree(path) # delete directory tree!
        return net
    else:
        return None

  def db_net_list(self):
    ''' returns list of active networks '''
    return [name for name in os.listdir(self.netpath)
              if os.path.isdir(os.path.join(self.netpath, name))]

  def db_net_listbyuid(self, uid):
    nets = self.db_net_list()
    ret = []
    for name in nets:
      uid_file = os.path.join(os.path.join(self.netpath, name), "uid")
      if os.path.isfile(uid_file):
        owner = int(next(open(uid_file)))
        if uid == owner:
          ret.append(name)
    return ret

  def db_net_get(self, net):
    ''' Verify network, return network path
        None is return for missing network
    '''
    ndir = os.path.join(self.netpath, str(net))
    if os.path.isdir(ndir):
        return ndir
    else:
        return None

  #  Node methods
  def db_node_get(self, node, net, count=None):
    ''' Return matching record(s)

        Upto 'count' many
    '''
    f = str(node)+":"+str(net)
    retlist=[]
    for file in os.listdir(self.data_node_path):
      if fnmatch.fnmatch(file, f):
        retlist.append(file)
        if count != None and len(retlist) == count:
          break
    return retlist

  def db_node_rm(self, node, net):
    ''' delete matching node record(s)
    '''
    f = str(node)+":"+str(net)
    for file in os.listdir(self.data_node_path):
        if fnmatch.fnmatch(file, f):
            os.remove(self.data_node_path+"/"+file)

  def db_node_set(self, node, net):
    ''' new node record '''
    self.db_node_rm(str(node), "*")
    fnew = self.data_node_path+ "/"+str(node)+":"+str(net)
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
