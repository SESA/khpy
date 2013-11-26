from kh_root import *
import getpass
import random
import string
import time

class KhProbe(KhRoot):
  def __init__(self, configsrc, dbpath):
    KhRoot.__init__(self, configsrc, dbpath)
    self.config = ConfigParser.SafeConfigParser()
    self.config.read(configsrc)
    self.db_path = dbpath
    self.job_path = os.path.join(self.db_path,
        self.config.get("BaseDirectories","jobdata"))
    self.data_job_path = os.path.join(self.db_path,
        self.config.get("BaseDirectories","job"))
    self.data_net_path = os.path.join(self.db_path,
        self.config.get("BaseDirectories","network"))

  # cli parser methods   ################################################

  def parse_clean(self, parser):
    parser = KhRoot.parse_clean(self, parser)
    parser.set_defaults(func=self.clean)
    return parser

  def parse_get(self, parser):
    parser = KhRoot.parse_get(self, parser)
    parser.set_defaults(func=self.get)
    return parser

  def parse_init(self, parser):
    parser = KhRoot.parse_init(self, parser)
    dcount=self.config.get('Probe','instance_max')
    parser.add_argument('-c', action=KH_store_optional, default=dcount,
        type=int, help='Instance count to initilaize')
    parser.set_defaults(func=self.init)
    return parser

  def parse_install(self, parser):
    parser.set_defaults(func=self.install)
    return parser

  def parse_rm(self, parser):
    parser = KhRoot.parse_rm(self, parser)
    parser.set_defaults(func=self.rm)
    return parser


  # action methods ####################################################

  def clean(self):
    self.db_net_rm('*','*')
    # end experiment 
    cmd = self.config.get('Probe', 'endcmd')
    subprocess.call(cmd, shell=True)
    # clean keyfile
    keysearch = "grep -v \"command='ssh\" " 
    keysearch += self.config.get('Probe', 'keyfile')
    keysearch += " > tmp && mv tmp "+self.config.get('Probe', 'keyfile')
    subprocess.call(keysearch, shell=True)
    # clean root directories
    print "Clean complete"
    KhRoot.clean(self)


  def get(self, job, count, option={}):
    nodes = KhRoot.get(self, job, count)
    # grab jobid from cookie?
    jobid = None
    for file in os.listdir(self.data_job_path):
      if fnmatch.fnmatch(file, job+":*"):
        jobid = str(file).split(':')[1];
    jobdir = self.job_path+'/'+str(jobid)
    # verify boot,config are files
    for n in nodes:
      r = self.db_net_get(n, '*')
      nip = str(r[r.find(':')+1:len(r)])
      # random filename for keygen
      keyfs = ''.join(random.choice(string.ascii_uppercase+string.digits) 
          for x in range(6))
      keypath = os.path.join(self.job_path,jobdir,n,keyfs)
      keycmd = "ssh-keygen -t rsa -b 768 -q -N '' -C "+nip+" -f "+keypath
      subprocess.call(keycmd, shell=True)
      # update authorized_keys file
      with open(self.config.get('Probe', 'keyfile'), "a") as outfile:
        with open(keypath+'.pub') as infile:
          outfile.write("command='ssh "+nip+"'")
          outfile.write(infile.read())
      
      # read in private key
      pkey = '' 
      pkey += open(keypath, 'rU').read()
      print pkey


  def init(self, option={}):
    count = int(self.config.get('Probe','instance_max'))
    listcmd = self.config.get('Probe', 'listcmd')
    imgcmd = self.config.get('Probe', 'imgloadcmd')
    expcmd = self.config.get('Probe', 'expcmd')
    # root cleanup
    KhRoot.init(self, count)
    # swap in experiment
    subprocess.call(expcmd, shell=True)
    # wait for job activate
    #print "Waiting for Probe experiment to swap in..."
    #waitcmd = cmd+" expwait -e SESA,"+exp+" active"
    #subprocess.call(waitcmd, shell=True)
    # record nodes names
    list = subprocess.check_output(listcmd, shell=True).split()
    print list
    for i in range(count):
      imgcmd += " "+list[i]
      self.db_net_set(i, list[i])
    # load our image
    subprocess.call(imgcmd, shell=True)



  def rm(self, job):
    if self.db_job_get(job, '*') == None:
      print "Error: no job record found"
      exit(1)
    nodes = KhRoot.db_node_get(self, '*', job, '*')
    keysearch = "grep -w -v \""
    reboot = self.config.get('Probe', 'rebootcmd')
    start = 0
    for n in nodes:
      nid = str(n[0:n.find(':')]) 
      # get network id
      rec =  self.db_net_get(nid, '*')
      netid = rec[rec.find(':')+1: len(rec)]
      # construct key search string
      if start == True:
        keysearch += "\|"
      else:
        start = True
      keysearch += netid
      reboot += " "+netid
    # Remove keys from authorized files
    keysearch += "\""+self.config.get('Probe', 'keyfile')
    keysearch += " > tmp && mv tmp "+self.config.get('Probe', 'keyfile')
    subprocess.call(keysearch, shell=True)
    # Reboot nodes on probe
    print "Rebooting probe nodes"
    subprocess.call(reboot, shell=True)
    KhRoot.rm(self,job)
      

  # database methods  ###################

  def db_net_get(self, node, net):
    f = str(node)+":"+str(net)
    for file in os.listdir(self.data_net_path):
      if fnmatch.fnmatch(file, f):
        return file
    return None
  
  def db_net_set(self, node, net):
    f = str(node)+":"+str(net)
    self.touch(self.data_net_path+'/'+f)

  def db_net_rm(self, node, net):
    f = str(node)+":"+str(net)
    for file in os.listdir(self.data_net_path):
        if fnmatch.fnmatch(file, f):
            os.remove(self.data_net_path+"/"+file)

  # utily ###################

  def instance_count(self):
    cmd = ""#hpcloud servers | grep ACTIVE | wc -l"
    return int(subprocess.check_output(cmd, shell=True))

  def reboot_count(self):
    cmd = "" #hpcloud servers | grep rebooting | wc -l"
    return int(subprocess.check_output(cmd, shell=True))

  # misc
  def test(self):
    print "You found hp!"
