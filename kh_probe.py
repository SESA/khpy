from kh_base import *
import getpass
import random
import string
import time

class KhProbe(KhRoot):
  def __init__(self, configsrc):
    KhRoot.__init__(self, configsrc)
    self.config = ConfigParser.SafeConfigParser()
    self.config.read(configsrc)
    self.db_path = os.getenv("KHDB")
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
    proj = self.config.get('Probe', 'proj')
    exp = self.config.get('Probe', 'exp')
    cmd = self.config.get('Probe', 'cmd')
    self.db_net_rm('*','*')
    cmd = cmd+" endexp -N -e "+proj+","+exp
    subprocess.call(cmd, shell=True)
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
      
      #####
      #load_config = "scp "+sshflags+' '+config.name+' '+user+"@"+ip+":"+config_path
      #load_app = "scp "+sshflags+' '+img.name+' '+user+"@"+ip+":"+app_path
      #load_kernel = "ssh "+sshflags+' '+user+"@"+ip+" sudo kexec -t multiboot-x86  --modu#le="+config_path+" -l "+app_path
      #boot_kernel = "ssh "+sshflags+" -f "+user+"@"+ip+" sudo kexec -e \ > /dev#/null 2>&1"
      #print subprocess.check_output(load_config, shell=True)
      #print subprocess.check_output(load_app, shell=True)
      #print subprocess.check_output(load_kernel, shell=True)
      #print subprocess.check_output(boot_kernel, shell=True)

    print "call into kh get (probe)", job, count, option


  def rm(self, job):
    if self.db_job_get(job, '*') == None:
      print "Error: no job record found"
      exit(1)
    nodes = KhRoot.db_node_get(self, '*', job, '*')
    for n in nodes:
      nid = str(n[0:n.find(':')])
      # reboot node
      cmd = "" #hpcloud servers:reboot kh_"+str(nid)
      subprocess.call(cmd, shell=True)
    while self.reboot_count() > 0:
      time.sleep(3)
    # TODO: verify ip persist across reboots
    KhRoot.rm(self,job)
      

  def init(self, option={}):
    exp = self.config.get('Probe', 'exp')
    count = int(self.config.get('Probe','instance_max'))
    cmd = self.config.get('Probe', 'cmd')
    # swap in experiment
    expcmd = self.config.get('Probe', 'expcmd')
    subprocess.call(expcmd, shell=True)
    print expcmd
    # wait for job activate
    print "Waiting for Probe experiment to swap in..."
    waitcmd = cmd+" expwait -e SESA,"+exp+" active"
    subprocess.call(waitcmd, shell=True)
    # record nodes names
    listcmd = cmd+" node_list -p -e SESA,"+exp
    list = subprocess.check_output(listcmd, shell=True).split()
    print list
    for i in range(count):
      print i, list[i]
      self.db_net_set(i, list[i])
    KhRoot.init(self, count)


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
