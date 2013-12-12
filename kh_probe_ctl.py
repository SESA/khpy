from kh_root import *
import getpass
import random
import re
import signal
import string
import subprocess
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
    parser.add_argument('key', nargs="+", action=KH_store_required, 
        type=str, help='Public key for channel')
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

  def console(self, nid):
    re1='.*?' # Non-greedy match 
    re2='(?:[a-z][a-z]*[0-9]+[a-z0-9]*)' # alphanum
    re3='(\\d+)'  # Integer 
    rg = re.compile(re1+re2+re1+'('+re2+')'+re1+re3,re.IGNORECASE|re.DOTALL)
    r = self.db_net_get(nid, '*')
    # verify valid id
    if r == None:
      print "Error, invalid node id"
    netid = r[r.find(':')+1: len(r)]

    # assume we have a valid destination
    mapfile = self.config.get('Probe', 'mapfile')
    entry = ""
    tn_server=""
    tn_port=""
    with open(mapfile) as f:
      for line in f: 
        if netid in line:
          entry = line
      if entry == "":
        print "Error: no entry found"
    m = rg.search(entry)
    if m:
      tn_server=m.group(1)
      tn_port=int(m.group(2))+2000
    else:
      print "Error: entry is garbage", entry

    # setup an SSH tunnel
    ssht = "ssh -fnNTL "+str(tn_port)+":"+tn_server+":"+str(tn_port)+" marmot"
    subprocess.call(ssht, shell=True)
    # get pid of latest ssh
    pid = int(subprocess.check_output("pgrep -n -x ssh", shell=True))
    # connect to telnet
    tn_cmd = "telnet localhost "+str(tn_port)
    subprocess.call(tn_cmd, shell=True)
    # kill ssh tunnel once user has closed telnet connection
    os.kill(pid, signal.SIGKILL)


  def clean(self):
    self.db_net_rm('*','*')
    # end experiment 
    cmd = self.config.get('Probe', 'endcmd')
    subprocess.call(cmd, shell=True)
    # clean keyfile
    keysearch = "grep -w -v \"command='ssh\" " 
    keysearch += self.config.get('Probe', 'keyfile')
    keysearch += " > tmp && mv tmp "+self.config.get('Probe', 'keyfile')
    subprocess.call(keysearch, shell=True)
    # clean root directories
    print "Clean complete"
    KhRoot.clean(self)

  def get(self, job, count, keybits):
    key = ''
    ## FIXME:
    # hard-code count == 1
    count = 1
    nodes = KhRoot.get(self, job, count)
    for i in range(len(keybits)):
      key += keybits[i]+" "
    for n in nodes:
      r = self.db_net_get(n, '*')
      nip = str(r[r.find(':')+1:len(r)])
      # add public key to authorized_keys file
      with open(self.config.get('Probe', 'keyfile'), "a") as outfile:
        outfile.write("command=\"ssh "+nip+" $SSH_ORIGINAL_COMMAND\" ")
        outfile.write(key+'\n')


  def init(self, option={}):
    count = int(self.config.get('Probe','instance_max'))
    listcmd = self.config.get('Probe', 'listcmd')
    imgcmd = self.config.get('Probe', 'imgloadcmd')
    expcmd = self.config.get('Probe', 'expcmd')
    # root cleanup
    KhRoot.init(self, count)
    # swap in experiment
    subprocess.call(expcmd, shell=True)
    # record nodes names
    list = subprocess.check_output(listcmd, shell=True).split()
    print list
    for i in range(count):
      imgcmd += " "+list[i]
      self.db_net_set(i, list[i])
    # load our image to nodes
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
      # return first match
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
