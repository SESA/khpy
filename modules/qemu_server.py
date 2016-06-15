import kh_server
from kh_server import *
import math
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

  def alloc_client(self, netid, count, img, config, option={}):
    # verify network 
    if not self.network_is_valid(netid):
      return "Error: network "+str(netid)+" is not valid"

    nodes = KhServer.alloc_client(self, netid, count)
    jobdir = self.netpath+'/'+str(netid)
    ret = ""
    ip_oct1 = str(int(netid) % 256)
    ip_oct2 = str(int(self.nid) % 256)
    hostip = "10."+ip_oct1+"."+ip_oct2+".1"
    n = "kh_"+ip_oct1
    
    # allocate nodes
    for node in nodes:
      ret += str(node)+"\n"
      nodedir = os.path.join(jobdir,str(node))
      nname = n+"_"+str(node)
      nodeip = "10."+ip_oct1+"."+ip_oct2+"."+str(((int(node)%254)+1))
      docker_run_cmd = "docker run -d --cap-add NET_ADMIN \
              --device  /dev/kvm:/dev/kvm --device /dev/net/tun:/dev/net/tun \
              --device /dev/vhost-net:/dev/vhost-net \
              --ip="+nodeip+" --net="+n+" --name="+nname
      docker_log_cmd = "docker logs -f "+nname
      qemu_args = " "

      # cid
      docker_run_cmd += " --cidfile=\""+nodedir+"/cid\""
      ret += nodedir+"/cid\n"
      # ram
      if option.has_key('ram') and option['ram'] > 0:
        docker_run_cmd += " -e VM_MEM="+str(option['ram'])+"G"
      # cpus 
      cpus = self.config.get("Qemu", "default_cpu") 
      if option.has_key('cpu') and option['cpu'] > 0:
        cpus= str(option['cpu']) 
        docker_run_cmd += " -e VM_CPU="+str(option['cpu'])
      # gdb debug 
      if option.has_key('g') and option['g'] > 0:
        gdb_port = int(self.config.get('Qemu', 'gdb_baseport')) + int(node)
        qemu_args += " -gdb tcp::"+str(gdb_port) 
        ret += "gdb: "+str(gdb_port)+"\n"
      # additional qemu commands
      if option.has_key('cmd') and len(option['cmd']) > 0:
        qemu_args += " "+option['cmd']+" " 
      # logs 
      ret += nodedir+"/stdout\n"
      ret += nodedir+"/stderr\n"
      docker_log_cmd += " > "+nodedir+"/stdout"
      docker_log_cmd += " 2> "+nodedir+"/stderr"
      docker_log_cmd = "( "+docker_log_cmd+" )&"

      ## image mounts
      if option.has_key('iso') and option['iso'] is 1:
        # load ISO image (assumed full OS)
        docker_run_cmd += " -v "+str(img)+":/tmp/image.iso"
        qemu_args += " /tmp/image.iso" 
      else:
        #kernel & config
        docker_run_cmd += " -v "+str(img)+":/tmp/krnl.elf"
        docker_run_cmd += " -v "+str(config)+":/tmp/initrd"
        qemu_args += " -kernel /tmp/krnl.elf"
        qemu_args += " -initrd /tmp/initrd"

      ## execute cmd 
      docker_run_cmd += " ebbrt/kvm-qemu:latest "+qemu_args
      with open(nodedir+"/cmd", 'a') as f:
        f.write(docker_run_cmd+"/n");
      ret += nodedir+"/cmd"
      if option.has_key('t') and option['t'] > 0:
        ret += "\nTEST RUN: docker instance was not allocated\n"
      else:
        #self._print(docker_run_cmd)
        #self._print(docker_log_cmd)
        subprocess.call(docker_run_cmd, shell=True, executable='/bin/bash')
        subprocess.call(docker_log_cmd, shell=True, executable='/bin/bash')

      #numa
      #numa = int(self.config.get("Qemu", "default_numa"))
      #if option.has_key('numa') and option['numa'] > 0:
      #  numa= int(option['numa'])
      #if numa > 1:
      #    cpu_per_node = int(math.floor(int(cpus)/int(numa)))
      #    for i in range(numa):
      #      cpu_list=""
      #      if cpu_per_node > 1:
      #        cpu_list=str(int(i*cpu_per_node))+"-"+str(((i+1)*(cpu_per_node))-1)
      #      else:
      #        cpu_list=str(int(i*cpu_per_node))
      #      qemu_args += " -numa node,cpus="+cpu_list
      # terminal signal fifo
      # if option.has_key('s') and option['s'] > 0:
      #     finish_cmd = "mkfifo "+nodedir+"/finish"
      #     subprocess.call(finish_cmd, shell=True)
      # pinning
      #if option.has_key('pin') and len(option['pin']) >= 0:
      #  pcmd = "taskset -a -c "+str(option['pin'])
      #  cmd = pcmd+' '+cmd 
      # perf
      #if option.has_key('perf')  :
      #  perf_cmd = self.config.get('Qemu','perf_cmd')+" -o "+nodedir+"/perf "
      #  if len(option['perf']) > 0:
      #    perf_cmd += option['perf']
      #  cmd = "( "+perf_cmd+" "+cmd+" ) </dev/null &"
      #  ret += nodedir+"/perf\n"
      #else:
      #  cmd = "("+cmd+")&"

    # end of per-node for-loop
    return ret

  def network_client(self,uid,option):
    netid = KhServer.network_client(self,uid)
    netpath = os.path.join(self.netpath, str(netid))
    ip_oct1 = str(int(netid) % 256)
    ip_oct2 = str(int(self.nid) % 256)
    hostip = "10."+ip_oct1+"."+ip_oct2+".1"
    n = "kh_"+ip_oct1
    b = "kh_"+ip_oct1+"B"
    t = "kh_"+ip_oct1+"T"
    docker_net_cmd = "docker network create -d bridge \
            -o \"com.docker.network.bridge.name\"=\""+b+"\"\
            -o \"com.docker.network.bridge.host_binding_ipv4\"=\""+hostip+"\" \
            --subnet="+hostip+"/16 \
            --ip-range="+hostip+"/24 "+n
    subprocess.check_output(docker_net_cmd, shell=True)
    return str(netid)+'\n'+str(hostip)

  def remove_network(self, netid, hostid="*"):
    if not self.network_is_valid(netid):
      return "Error: network "+str(netid)+" is not valid"
    ip_oct1 = str(int(netid) % 256)
    ip_oct2 = str(int(self.nid) % 256)
    hostip = "10."+ip_oct1+"."+ip_oct2+".1"
    n = "kh_"+ip_oct1
    b = "kh_"+ip_oct1+"B"
    t = "kh_"+ip_oct1+"T"
    docker_netrm_cmd = "docker network rm "+n
    # remove nodes on network
    netdir = os.path.join(self.netpath, str(netid))
    nodes = self.db_node_get('*', netid)
    for node in nodes:
      nid = node[0:node.find(':')]
      self.remove_node(nid)
    # docker network rm
    try:
      subprocess.check_output(docker_netrm_cmd, shell=True)
    except subprocess.CalledProcessError:
      pass
    # remove network record
    return KhServer.remove_network(self, netid, hostid)

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
    # verify node 
    if not self.node_is_valid(node):
      return "Error: node "+str(node)+" is not valid"
    nodes = self.db_node_get(node, '*')
    noderec = nodes[0]
    if noderec is not None:
      splits = noderec.split(':')
      netid = splits[1] 
    else:
      return "Error: no network for node #"+str(node)
    netdir = os.path.join(self.netpath, str(netid))
    nodedir = os.path.join(netdir, str(node))
    cidpath=os.path.join(nodedir, 'cip')
    if os.path.exists(cidpath):
      # read pid, remove process
      with open(cidpath, 'r') as f:
        cid = f.readline()
        f.close()
        try:
          subprocess.check_output("docker stop "+str(cid) ,shell=True) 
          subprocess.check_output("docker rm "+str(cid) ,shell=True) 
        except subprocess.CalledProcessError:
          pass
    else:
      return "Error: could not verify cid" 
    return KhServer.remove_node(self, node, netid)

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
    path = '/dev/random'
    if path:
     return '0x%016x' % int(os.stat(path)[stat.ST_INO])
    else:
      return None
  
  def vdesock_path(self,nid):
    return os.path.join(os.path.join(self.netpath, str(nid)), 'vde_sock')

  def tap_path(self,nid):
    return os.path.join(os.path.join(self.netpath, str(nid)), 'tap')
