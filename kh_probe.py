from kh_base import *
import getpass
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
    parser.add_argument('img', action=KH_store_required,
        type=file, help='Path to application')
    parser.add_argument('config', action=KH_store_required,
        type=file, help='Path to configuration')
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
    cmd = cmd+" endexp -e "+proj+","+exp
    subprocess.call(cmd, shell=True)
    KhRoot.clean(self)

  def get(self, job, count, img, config, option={}):
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
      #ip = str(r[r.find(':')+1:len(r)])
      #sshflags = self.config.get('HpCloud','sshopt')
      #user = self.config.get('HpCloud','user')
      #config_path = self.config.get('HpCloud','config')
      #app_path = self.config.get('HpCloud','app')
      #####
      #load_config = "scp "+sshflags+' '+config.name+' '+user+"@"+ip+":"+config_path
      #load_app = "scp "+sshflags+' '+img.name+' '+user+"@"+ip+":"+app_path
      #load_kernel = "ssh "+sshflags+' '+user+"@"+ip+" sudo kexec -t multiboot-x86 \
#--modu#le="+config_path+" -l "+app_path
      #boot_kernel = "ssh "+sshflags+" -f "+user+"@"+ip+" sudo kexec -e \
#> /dev#/null 2>&1"

      #print subprocess.check_output(load_config, shell=True)
      #print subprocess.check_output(load_app, shell=True)
      #print subprocess.check_output(load_kernel, shell=True)
      #print subprocess.check_output(boot_kernel, shell=True)

    print "call into hpget", job, count, option

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
    # wait for job tobe  active
    print "Waiting for Probe experiment to swap in..."
    waitcmd = cmd+" expwait -e SESA,"+exp+" active"
    subprocess.call(waitcmd, shell=True)
    # record ids of nodes
    listcmd = cmd+" node_list -p -e SESA,"+exp
    list = subprocess.check_output(listcmd, shell=True).split()
    for i in range(len(list)):
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
