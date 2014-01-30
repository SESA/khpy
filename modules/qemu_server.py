from kh_server import *
import os
import stat

class QemuServer(KhServer):
  def __init__(self, configsrc):
    KhServer.__init__(self, configsrc)
    self.config = ConfigParser.SafeConfigParser()
    self.config.read(configsrc)
    self.db_path = self.config.get("database","path")
    self.netpath = os.path.join(self.db_path,
        self.config.get("BaseDirectories","jobdata"))
    self.data_net_path = os.path.join(self.db_path,
        self.config.get("BaseDirectories","job"))

  # cli parser methods   ###############################################

  def parse_install(self, parser):
    parser = KhServer.parse_install(self, parser)
    parser.set_defaults(func=self.install)
    return parser

  def parse_down(self, parser):
    parser = KhServer.parse_down(self, parser)
    parser.set_defaults(func=self.down)
    return parser

  def parse_up(self, parser):
    parser = KhServer.parse_up(self, parser)
    parser.set_defaults(func=self.up)
    return parser

  def parse_clean(self, parser):
    parser = KhServer.parse_clean(self, parser)
    parser.set_defaults(func=self.clean)
    return parser

  def parse_info(self, parser):
    parser = KhServer.parse_info(self, parser)
    parser.set_defaults(func=self.info)
    return parser

  # action methods #############################################

  def alloc_client(self, nid, count, img, config, option={}):
    nodes = KhServer.alloc_client(self, nid, count)
    #jobid = None
    ## grab jobid from cookie?
    #for file in os.listdir(self.data_net_path):
    #  if fnmatch.fnmatch(file, nid+":*"):
    #    jobid = str(file).split(':')[1];
    jobdir = self.netpath+'/'+str(nid)

    for node in nodes:
      nodedir = jobdir+'/'+str(node)
      ''' construct qemu line '''
      cmd = self.config.get('Qemu', 'cmd')
      # gdb debug server
      if option.has_key('g') and option['g'] > 0:
        cmd += " -gdb tcp::"+option['g']
        option['g'] = str(int(option['g'])+1)
      ## internal network
      #if option.has_key('i') and option['i'] == True:
      #  mac = self.generate_mac(node)
      #  cmd +=" -net nic,vlan=1,model=virtio,macaddr="+mac+" \
      #    -net bridge,vlan=2,br=brI"
      ## external network
      #if option.has_key('x') and option['x'] == True:
      #  mac = self.generate_mac(node)
      #  cmd +=" -net nic,vlan=2,model=virtio,macaddr="+mac+" \
      #    -net bridge,vlan=2,br=brX"
      # serial log
      cmd += " -serial file:"+nodedir+"/serial.log"
      # vnc socket
      cmd += " -vnc unix:"+nodedir+"/vnc"
      # ram
      cmd += " -m "+self.config.get('Qemu', 'ram')
      # pid
      cmd += " -pidfile "+nodedir+"/pid"
      # kernel 
      cmd += " "+img+" "
      #cmd += " -kernel "+str(img)
      # config
      #cmd += " -initrd "+str(config)
      # error log (end of command)
      cmd += " > "+nodedir+"/error.log 2>&1 &" 
      print cmd
      subprocess.call(cmd, shell=True)
      return "Node allocation sucessful" 

  def network(self):
    nid = KhServer.network(self)
    #if nid == None:
    #  print "Error: network '"+name+"' already exists"
    #  exit(1)
    # TODO: move all this into a config file
    user = "root"
    tapcmd = "tunctl -b -u "+user
    netmask = "255.255.255.0"
    hostip = "10."+str(nid)+"."+str(nid)+".1"
    dhcp_start = "10."+str(nid)+"."+str(nid)+".50"    
    dhcp_end = "10."+str(nid)+"."+str(nid)+".150"    
    netpath = os.path.join(self.netpath, str(nid))

    # generate tap
    tapfile = os.path.join(netpath, 'tap')
    KhServer.touch(self,tapfile)
    tap = subprocess.check_output(tapcmd, shell=True).rstrip()
    if os.path.isfile(tapfile) == 1:
      with open(tapfile, "a") as f:
        f.seek(0)
        f.truncate()
        f.write(str(tap))

    # configure interface
    ipcmd = "ifconfig "+tap+" "+hostip+" netmask "+netmask+" up"
    # enable dhcp
    dnscmd = "dnsmasq --pid-file="+netpath+"/dnsmasq --listen-address="+hostip+" -z \
--dhcp-range="+dhcp_start+","+dhcp_end+",12h"
    # start virtual network
    vdecmd = "vde_switch -sock "+netpath+"/vde_sock -daemon -tap "+tap+" -M \
"+netpath+"/vde_mgmt -p "+netpath+"/vde_pid"
    subprocess.check_output(ipcmd, shell=True)
    subprocess.check_output(dnscmd, shell=True)
    subprocess.check_output(vdecmd, shell=True)
    return nid


  def remove(self, net):
    netinfo = self.db_job_get(net, '*')
    if(netinfo == None):
      print "Error: network ",net," not found."
      exit(1)
    netid = netinfo[netinfo.find(':')+1:len(netinfo)]
    nodes = self.db_node_get('*', net, netid)
    # remove processes
    for node in nodes:
      nid = node[0:node.find(':')]
      path = self.netpath+'/'+str(netid)+'/'+str(nid)+'/pid'
      if os.path.exists(path):
        with open(path, 'r') as f:
          pid = int(f.readline())
          f.close()
        try:
          os.kill(pid,15) 
        except OSError:
          print "Warning: process",pid,"not found."
          pass
    # remove record
    KhServer.remove(self, net)

# As per "standards" lookuping up on the net
# the following are locally admined mac address
# ranges:
#
#x2-xx-xx-xx-xx-xx
#x6-xx-xx-xx-xx-xx
#xA-xx-xx-xx-xx-xx
#xE-xx-xx-xx-xx-xx
# format we use 02:f(<inode>):nodenum
# ip then uses prefix 10.0 with last to octets of mac
  def generate_mac(self, nid):
    sig = str(self.inode())
    nodeid = '0x%02x' % int(nid)
    macprefix="02:"+sig[10:12]+':'+sig[12:14]+':'+sig[14:16]+':'+sig[8:10]
    mark = nodeid.find('x')
    return macprefix+':'+nodeid[mark+1:mark+3]
  
  def inode(self):
    path = (os.path.abspath(__file__))
    if path:
     return '0x%016x' % int(os.stat(path)[stat.ST_INO])
    else:
      return None

