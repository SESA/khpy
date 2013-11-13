from kh_base import *
import os

class KhQemu(KhBase):
  def __init__(self, configsrc):
    KhBase.__init__(self, configsrc)
    self.config = ConfigParser.SafeConfigParser()
    self.config.read(configsrc)
    self.db_path = os.getenv("KHDB")
    self.data_job_path = os.path.join(self.db_path,
        self.config.get("BaseDirectories","job"))
  # cli parser methods   ################################################

  def parse_get(self, parser):
    parser = KhBase.parse_get(self, parser)
    parser.add_argument('img', action=KH_store_required,
        type=str, help='Path to application')
    parser.add_argument('config', action=KH_store_required,
        type=str, help='Path to configuration')
    parser.add_argument('-i', action=KH_store_optional_const,
        const=True, default=False, help='Enable internal network')
    parser.add_argument('-x', action=KH_store_optional_const,
        const=True, default=False, help='Enable external network')
    parser.add_argument('-f', action=KH_store_optional_const,
        const=True, default=False, help="Enable frontend,\
        equivalent to '-i -x'")
    parser.add_argument('-g', action=KH_store_optional,
        help='GDB debug starting port number')
    parser.set_defaults(func=self.get)
    return parser

  def parse_rm(self, parser):
    parser = KhBase.parse_rm(self, parser)
    parser.set_defaults(func=self.rm)
    return parser

  def parse_setup(self, parser):
    parser = KhBase.parse_setup(self, parser)
    parser.set_defaults(func=self.setup)
    return parser

  # action methods ####################################################

  def get(self, job, count, bootimg, config, option={}):
    nodes = KhBase.get(self, job, count)
      # TODO: print cookie?
    
    jobid = None
    # todo jobid in cookie?
    for file in os.listdir(self.data_job_path):
      if fnmatch.fnmatch(file, job+":*"):
        jobid = str(file).split(':')[1];

    jobdir = self.data_job_path+'/'+str(jobid)

    for node in nodes:
      nodedir = jobdir+'/'+str(node)
      ''' construct qemu line '''
      cmd = self.config.get('Qemu', 'cmd')

      # gdb debug server
      if option.has_key('g') and option['g'] > 0:
        cmd += " -gdb tcp::"+option['g']
        option['g'] = str(int(option['g'])+1)
      # internal network
      if option.has_key('i') and option['i'] == True:
        cmd += " -net nic,vlan=1,model=virtio -net bridge,vlan=2,br=brI"
      # external network
      if option.has_key('x') and option['x'] == True:
        cmd += " -net nic,vlan=2,model=virtio -net bridge,vlan=2,br=brX"
      # serial log
      cmd += " -serial file:"+nodedir+"/serial.log"
      # vnc socket
      cmd += " -vnc unix:"+nodedir+"/vnc"
      # ram
      cmd += " -m "+self.config.get('Qemu', 'ram')
      # pid
      cmd += " -pidfile "+nodedir+"/pid"
      # kernel 
      cmd += " -kernel "+str(bootimg)
      # config
      cmd += " -initrd "+str(config)
      # error log (end of command)
      cmd += " >"+nodedir+"/error.log 2>&1" 

      print cmd


  def rm(self, job):
    print "qemu rm logic"
    KhBase.rm(self, job)

  def setup(self):
    KhBase.setup(self)
    print "qemu setup logic"
