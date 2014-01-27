from kh_root import *
import time

class KhHpCloud(KhBase):
  def __init__(self, configsrc, dbpath):
    KhBase.__init__(self, configsrc, dbpath)
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
    parser = KhBase.parse_clean(self, parser)
    parser.set_defaults(func=self.clean)
    return parser

  def parse_get(self, parser):
    parser = KhBase.parse_get(self, parser)
    parser.add_argument('img', action=KH_store_required,
        type=file, help='Path to application')
    parser.add_argument('config', action=KH_store_required,
        type=file, help='Path to configuration')
    parser.set_defaults(func=self.get)
    return parser

  def parse_init(self, parser):
    parser = KhBase.parse_init(self, parser)
    dcount=self.config.get('HpCloud','instance_max')
    parser.add_argument('-c', action=KH_store_optional, default=dcount,
        type=int, help='Instance count to initilaize')
    parser.set_defaults(func=self.init)
    return parser

  def parse_install(self, parser):
    parser.set_defaults(func=self.install)
    return parser

  def parse_rm(self, parser):
    parser = KhBase.parse_rm(self, parser)
    parser.set_defaults(func=self.rm)
    return parser


  # action methods ####################################################

  def clean(self):
    nodes = KhBase.db_node_get(self, '*', '*', '*')
    for n in nodes:
      nid = str(n[0:n.find(':')])
      # kill node
      cmd = "hpcloud servers:remove kh_"+str(nid)
      subprocess.call(cmd, shell=True)
      # TODO: clean net records
    KhBase.clean(self)

  def get(self, job, count, img, config, option={}):
    nodes = KhBase.get(self, job, count)
    # grab jobid from cookie?
    jobid = None
    for file in os.listdir(self.data_job_path):
      if fnmatch.fnmatch(file, job+":*"):
        jobid = str(file).split(':')[1];
    jobdir = self.job_path+'/'+str(jobid)
    # verify boot,config are files
    for n in nodes:
      r = self.db_net_get(n, '*')
      ip = str(r[r.find(':')+1:len(r)])

      sshflags = self.config.get('HpCloud','sshopt')
      user = self.config.get('HpCloud','user')
      config_path = self.config.get('HpCloud','config')
      app_path = self.config.get('HpCloud','app')
      ####
      load_config = "scp "+sshflags+' '+config.name+' '+user+"@"+ip+":"+config_path
      load_app = "scp "+sshflags+' '+img.name+' '+user+"@"+ip+":"+app_path
      load_kernel = "ssh "+sshflags+' '+user+"@"+ip+" sudo kexec -t multiboot-x86 \
--module="+config_path+" -l "+app_path
      boot_kernel = "ssh "+sshflags+" -f "+user+"@"+ip+" sudo kexec -e \
> /dev/null 2>&1"

      print subprocess.check_output(load_config, shell=True)
      print subprocess.check_output(load_app, shell=True)
      print subprocess.check_output(load_kernel, shell=True)
      print subprocess.check_output(boot_kernel, shell=True)

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
    nodes = KhBase.db_node_get(self, '*', job, '*')
    for n in nodes:
      nid = str(n[0:n.find(':')])
      # reboot node
      cmd = "hpcloud servers:reboot kh_"+str(nid)
      subprocess.call(cmd, shell=True)
    while self.reboot_count() > 0:
      time.sleep(3)
    # TODO: verify ip persist across reboots
    KhBase.rm(self,job)
      
  def init(self, option={}):
    if option.has_key('c') and c>0:
      count = option['c']
    else:
      count = int(self.config.get('HpCloud','instance_max'))
    allocated = self.instance_count() + count
    for i in range(count):
      cmd = "hpcloud servers:add kh_"+str(i)+" xsmall --key_name ssh &"
      subprocess.call(cmd, shell=True)
    # spin until all instances are online
    while self.instance_count() < allocated:
      time.sleep(3)
    # record ips to db
    for i in range(count):
      cmd="hpcloud servers -d ' ' kh_"+str(i)+" | grep ACTIVE \
          | while read nid state fla img ip junk; do echo -n $ip; done"
      ip=subprocess.check_output(cmd, shell=True)
      self.db_net_set(i, ip)
    # setup remaining db records
    KhBase.init(self, count)


  # database methods  ###################

  def db_net_get(self, node, netid):
    f = str(node)+":"+str(netid)
    for file in os.listdir(self.data_net_path):
      if fnmatch.fnmatch(file, f):
        return file
    return None
  
  def db_net_set(self, job, net):
    f = str(job)+":"+str(net)
    self.touch(self.data_net_path+'/'+f)

  # utily ###################

  def instance_count(self):
    cmd = "hpcloud servers | grep ACTIVE | wc -l"
    return int(subprocess.check_output(cmd, shell=True))

  def reboot_count(self):
    cmd = "hpcloud servers | grep rebooting | wc -l"
    return int(subprocess.check_output(cmd, shell=True))

  # misc
  def test(self):
    print "You found hp!"
