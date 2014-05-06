import kh_server
from kh_server import *
import os
import stat
import time

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

#action methods############################################ #

  def server_config(self):
    return KhServerConfig(self.config.get('Qemu', 'server_ip'),
      self.config.get('Qemu', 'server_port'),
      self.config.get('Qemu', 'pidfile_path'),
      self.config.get('Qemu', 'stdin_path'),
      self.config.get('Qemu', 'stdout_path'),
      self.config.get('Qemu', 'stderr_path'))

  def alloc_client(self, nid, count, img, config, option={}):

    # verify  network is legit
    if not self.network_is_valid(nid):
      return "Error: network "+str(nid)+" is not valid"

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
      # networking
      mac = self.generate_mac(node)
      ret += mac+"\n"
      # vhost kludge
      if option.has_key('vhost') and option['vhost'] is 1:
        tapfile = self.tap_path(nid)
        tap=str(next(open(tapfile)))
        cmd += " --netdev tap,id=vlan1,ifname="+tap+",script=no,downscript=no,vhost=on --device virtio-net,netdev=vlan1,mac="+mac
      else: 
        #vde switch
        vdesock = self.vdesock_path(nid)
        cmd +=" -net nic,vlan=1,model=virtio,macaddr="+mac+" \
            -net vde,vlan=1,sock="+vdesock
     
     # gdb debug server
      if option.has_key('g') and option['g'] > 0:
        gdb_port = int(self.config.get('Qemu', 'gdb_baseport')) + int(node)
        cmd += " -gdb tcp::"+str(gdb_port) 
        ret += "gdb: "+str(gdb_port)+"\n"
      # serial log
      cmd += " -serial file:"+nodedir+"/serial.log"
      ret += nodedir+"/serial.log\n"
      # ram
      cmd += " -m "+self.config.get('Qemu', 'ram')
      # pid
      cmd += " -pidfile "+nodedir+"/pid"
      # display
      cmd += " -display none "

      # load image
      if option.has_key('iso') and option['iso'] is 1:
        # load ISO image (assumed full OS)
        cmd += " "+str(img)
      else:
        #kernel & config
        cmd += " -kernel "+str(img)
        cmd += " -initrd "+str(config)

      # error log (end of command)
      cmd += " > "+nodedir+"/error.log 2>&1 &" 
      ret += nodedir+"/error.log\n"
      print cmd
      # touch serial file to set the correct permissions
      touch(nodedir+'/serial.log')
      subprocess.call(cmd, shell=True)
    return ret

  def network_client(self,uid,option):
    nid = KhServer.network_client(self,uid)
    user = "root"
    tapcmd = "tunctl -b -u "+user
    netmask = "255.255.255.0"

    ip_oct1 = str(int(nid / 256)+1)
    ip_oct2 = str((nid % 256))
    hostip = "10."+ip_oct1+"."+ip_oct2+".1"
    dhcp_start = "10."+ip_oct1+"."+ip_oct2+".50"    
    dhcp_end = "10."+ip_oct1+"."+ip_oct2+".150"    
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

    # vhost kludge - exit before dhcp or vdeswitch
    if option.has_key('vhost') and option['vhost'] is 1:
      subprocess.check_output(ipcmd, shell=True)
      return str(nid)+'\n'+str(hostip)

    # local dhcp on interface
    dnscmd = "dnsmasq --pid-file="+netpath+"/dnsmasq --listen-address="+hostip+" -z \
--log-facility="+netpath+"/dnsmasq.log \
--dhcp-range="+dhcp_start+","+dhcp_end+",12h"
    # start virtual network
    vdecmd = "vde_switch -sock "+netpath+"/vde_sock -daemon -tap "+tap+" -M \
"+netpath+"/vde_mgmt -p "+netpath+"/vde_pid"
    subprocess.check_output(ipcmd, shell=True)
    subprocess.check_output(dnscmd, shell=True)
    subprocess.check_output(vdecmd, shell=True)
    return str(nid)+'\n'+str(hostip)

  def _kill(self, path):
    if os.path.exists(path):
      # read pid, remove process
      with open(path, 'r') as f:
        pid = int(f.readline())
        f.close()
      try:
        os.kill(pid,15) 
      except OSError:
        self._print("Warning: process "+str(pid)+" not found")
        pass
    else:
      self._print("Warning: file "+str(path)+" not found")

  def remove_node(self, node):
    # verify  node is legit
    if not self.node_is_valid(node):
      return "Error: node "+str(node)+" is not valid"

    nodes = self.db_node_get(node, '*')
    noderec = nodes[0]
    if noderec is not None:
      netid = noderec[noderec.find(':')+1:len(noderec)]
    else:
      return "Error: no network for node #"+str(node)

    netdir = os.path.join(self.netpath, str(netid))
    self._kill(os.path.join(os.path.join(os.path.join(netdir,
      str(node)),'pid')))
    return KhServer.remove_node(self, node, netid)
    
  def remove_network(self, netid):
    # verify  network is legit
    if not self.network_is_valid(netid):
      return "Error: network "+str(netid)+" is not valid"
    # get node records
    netdir = os.path.join(self.netpath, str(netid))
    nodes = self.db_node_get('*', netid)
    for node in nodes:
      nid = node[0:node.find(':')]
      self._kill(os.path.join(os.path.join(os.path.join(netdir,
        str(nid)),'pid')))
    # remove dnsmasq
    self._kill(os.path.join(os.path.join(netdir, 'dnsmasq')))
    # remove vde_switch
    self._kill(os.path.join(os.path.join(netdir, 'vde_pid')))
    # remove tap
    tappath=os.path.join(netdir, 'tap')
    if os.path.exists(tappath):
      # read pid, remove process
      with open(tappath, 'r') as f:
        tap = f.readline()
        f.close()
        print subprocess.check_output('tunctl -d '+tap, shell=True)
    # remove records
    return KhServer.remove_network(self, netid)

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

  def tap_path(self,nid):
    return os.path.join(os.path.join(self.netpath, str(nid)), 'tap')
