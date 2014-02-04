import kh_server
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

  # cli parser methods   #######################################

  def parse_install(self, parser):
    parser = KhServer.parse_install(self, parser)
    parser.set_defaults(func=self.install)
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

  def server_config(self):
    return KhServerConfig(self.config.get('Qemu', 'server_ip'),
      self.config.get('Qemu', 'server_port'),
      self.config.get('Qemu', 'pidfile_path'),
      self.config.get('Qemu', 'stdin_path'),
      self.config.get('Qemu', 'stdout_path'),
      self.config.get('Qemu', 'stderr_path'))

  def alloc_client(self, nid, count, img, config, option={}):
    nodes = KhServer.alloc_client(self, nid, count)
    jobdir = self.netpath+'/'+str(nid)
    ret = ""
    # allocate nodes
    print "Allocating nodes: ",nodes
    for node in nodes:
      ret += str(node)+"\n"
      nodedir = jobdir+'/'+str(node)
      ''' construct qemu line '''
      cmd = self.config.get('Qemu', 'cmd')

      # gdb debug server
      if option.has_key('g') and option['g'] > 0:
        cmd += " -gdb tcp::"+option['g']
        option['g'] = str(int(option['g'])+1)

      # networking
      mac = self.generate_mac(node)
      ret += mac+"\n"
      vdesock = self.vdesock_path(nid)
      cmd +=" -net nic,vlan=1,model=virtio,macaddr="+mac+" \
          -net vde,vlan=1,sock="+vdesock

      ## internal network
      #if option.has_key('i') and option['i'] == True:
      #  cmd +=" -net nic,vlan=1,model=virtio,macaddr="+mac+" \
      #    -net bridge,vlan=2,br=brI"

      ## external network
      #if option.has_key('x') and option['x'] == True:
      #  mac = self.generate_mac(node)
      #  cmd +=" -net nic,vlan=2,model=virtio,macaddr="+mac+" \
      #    -net bridge,vlan=2,br=brX"
       
      # serial log
      cmd += " -serial file:"+nodedir+"/serial.log"
      ret += nodedir+"/serial.log\n"
      # vnc socket
      cmd += " -vnc unix:"+nodedir+"/vnc"
      # ram
      cmd += " -m "+self.config.get('Qemu', 'ram')
      # pid
      cmd += " -pidfile "+nodedir+"/pid"
      # kernel 
      cmd += " -kernel "+str(img)
      # config
      cmd += " -initrd "+str(config)
      # error log (end of command)
      cmd += " > "+nodedir+"/error.log 2>&1 &" 
      print cmd
      subprocess.call(cmd, shell=True)
    return ret

  def network_client(self):
    nid = KhServer.network_client(self)
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
    kh_server.touch(tapfile)
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
    return str(nid)+'\n'+str(hostip)


  def remove(self, net):
    #netinfo = self.db_job_get(net, '*')
    #if(netinfo == None):
    #  print "Error: network ",net," not found."
    #  exit(1)
    #netid = netinfo[netinfo.find(':')+1:len(netinfo)]

    # verify directoy exists, i.e., network is legit
    ndir = os.path.join(self.netpath, str(net))
    if not os.path.isdir(ndir):
      self._print("Error: network "+str(net)+" not found")
      exit(1)

    nodes = self.db_node_get('*', netid)
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
          self._print("Warning: process "+pid+" not found.")
          pass
    # remove dnsmasq
    # remove vde_switch
    # remove tap
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
    path = '/opt/khpy/kh'
    if path:
     print path
     return '0x%016x' % int(os.stat(path)[stat.ST_INO])
    else:
      return None
  
  def vdesock_path(self,nid):
    return os.path.join(os.path.join(self.netpath, str(nid)), 'vde_sock')

