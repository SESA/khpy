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
import shutil
import subprocess

def _ensure_value(namespace, name, value):
    if getattr(namespace, name, None) is None:
        setattr(namespace, name, value)
    return getattr(namespace, name)

# our custom parameterizer
class Parameterize(argparse.Action):
  def __call__(self, parser, namespace, values, option_string=None):
    items = copy.copy(_ensure_value(namespace, 'args', []))
    items.append(self.dest)
    setattr(namespace, 'args', items)
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
    self.data_job_path = os.path.join(self.db_path,
        self.config.get("BaseDirectories","job"))

  # cli parser methods   ################################################

  def parse_clean(self, parser):
    parser.set_defaults(func=self.clean)
    return parser

  def parse_get(self, parser):
    parser.set_defaults(func=self.get)
    parser.add_argument('job', action=Parameterize, help="Name of job")
    parser.add_argument('count', type=int, action=Parameterize, help="Amount of\
        instances")
    return parser

  def parse_info(self, parser):
    parser.set_defaults(func=self.info)
    return parser

  def parse_install(self, parser):
    parser.set_defaults(func=self.install)
    return parser

  def parse_rm(self, parser):
    parser.add_argument('job', action=Parameterize, help="Name of job")
    parser.set_defaults(func=self.rm)
    return parser

  def parse_setup(self, parser):
    parser.set_defaults(func=self.setup)
    return parser

  # action methods ####################################################

  def clean(self):
    ''' remove node files '''
    self.db_node_rm('*','*','*')
    self.db_job_rm('*','*')
    ''' remove job data subdirectories '''
    datapath = os.path.join(self.db_path,
        self.config.get("BaseDirectories", "jobdata"))
    shutil.rmtree(datapath)
    os.mkdir(datapath)

  def get(self, job, count):
    ''' 
    Input: job name, instance count
    '''
    #check if job record exists
    jobid = None
    for file in os.listdir(self.data_job_path):
      if fnmatch.fnmatch(file, job+":*"):
        jobid = str(file).split(':')[1];
        break
    if jobid == None: #if not, setup new job
      jobid = self.db_job_set(job) 

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
      print("Warning: looks like we're out of nodes")
      exit(1)

    # assign nodes
    gotlist = []
    for node in nodes:
      nid = node[0:node.find(':')]
      gotlist.append(nid)
      self.db_node_set(nid, job, jobid)
      if os.path.exists(datapath+'/'+str(nid)) == 0:
        os.mkdir(datapath+'/'+str(nid))

    print(gotlist)
    return gotlist


  def info(self):
    # list each app and the number of nodes
    for file in os.listdir(self.data_job_path):
      job = file[0:file.find(':')]
      jobid = file[file.find(':')+1:len(file)]
      nodes = self.db_node_get('*',job,jobid)
      print (job, jobid, len(nodes))


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

  def rm(self, job):
    jobid = self.db_job_rm(job)
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


  def setup(self, count=0):
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
        f = open(self.db_path+'/'+self.config.get('BaseFiles', s), 'w')
        print(self.config.get('Defaults',s), file=f)
        f.close()



  # database methods ################################################

  ''' TODO
    - method to remove a list of nodes ?
  '''

  # return filename of first matching job record
  def db_job_get(self, job, jobid):
    f = str(job)+":"+str(jobid)
    for file in os.listdir(self.data_job_path):
      if fnmatch.fnmatch(file, f):
        return file
    return None

  # Grab next jobid and assign it to job
  # TODO: move id assignment login into get()?
  def db_job_set(self, job): 
    rid=int(next(open(self.db_path+'/'+self.config.get('BaseFiles','jobid'))))
    nextid=rid+1
    print('rid=',rid,'nexid=',nextid)
    # increase jobid count
    f = open(self.db_path+'/'+self.config.get('BaseFiles', 'jobid'), 'w')
    print(nextid, file=f)
    f.close()
    # setup db record
    rpath = self.db_path+'/'+self.config.get('BaseDirectories','job')+\
      '/'+str(job)+':'+str(rid)
    self.touch(rpath)
    return rid

  # remove DB record, return (expired) jobid
  def db_job_rm(self, job, jobid=None):
    if jobid == None:
      record = self.db_job_get(job, '*')
      jobid = record[record.find(':')+1:len(record)]
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
  
  # utility functions ################################################

  # create empty file
  def touch(self, fname, times=None):
    with file(fname, 'a'):
      os.utime(fname, times)

  def test(self):
    print( "You found base!")
