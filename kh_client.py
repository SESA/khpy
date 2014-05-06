from kh_shared import *
import ConfigParser 
import getpass
import random
import string
import time
import os
import xmlrpclib

# Kittyhawk root server object
class KhClient():
  def __init__(self, configsrc):
    self.config = ConfigParser.SafeConfigParser()
    self.config.read(configsrc)
    self.address = "http://"+self.config.get('Qemu','server_ip')+":"+self.config.get('Qemu', 'server_port')
    self.proxy = xmlrpclib.ServerProxy(self.address)

  # Defailt commmand parsers ################################################

  def add_parsers(self, subpar):
    # alloc
    self.parse_alloc(subpar.add_parser('alloc', 
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
      description="Allocate node for a given network"))
    # clean
    self.parse_clean(subpar.add_parser('clean',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
      description="Remove network, reset nodes"))
    # console
    self.parse_console(subpar.add_parser('console',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
      description="Get broadcast console on network"))
    # info
    self.parse_info(subpar.add_parser('info',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
      description="List my networks and nodes"))
    # network
    self.parse_network(subpar.add_parser('network', 
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
      description="Allocate a network"))
    # remove node
    self.parse_remove_node(subpar.add_parser('rmnode',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
      description="Remove network and free allocated nodes"))
    # remove network
    self.parse_remove_network(subpar.add_parser('rmnet',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
      description="Remove network and free allocated nodes"))


  def parse_alloc(self, parser):
    parser.set_defaults(func=self.alloc)
    parser.add_argument('network',type=str,action=KH_store_required, 
      help="Network id")
    parser.add_argument('img', action=KH_store_required,
        type=str, help='path to application')
    parser.add_argument('config', action=KH_store_required,
        type=str, help='path to configuration')
    parser.add_argument('-n', action=KH_store_optional, type=int,
    metavar='num', help='Number of nodes')
    return parser

  def parse_clean(self, parser):
    parser.set_defaults(func=self.clean)
    return parser

  def parse_console(self, parser):
    parser.add_argument('key',action=KH_store_required,
      help="Instance identifier")
    parser.set_defaults(func=self.console)
    return parser

  def parse_info(self, parser):
    parser.set_defaults(func=self.info)
    return parser

  def parse_network(self, parser):
    parser.set_defaults(func=self.network)
    return parser

  def parse_remove_network(self, parser):
    parser.add_argument('net', action=KH_store_required,
      help="Network ID")
    parser.set_defaults(func=self.remove_network)
    return parser

  def parse_remove_node(self, parser):
    parser.add_argument('node', action=KH_store_required,
      help="Node ID")
    parser.set_defaults(func=self.remove_node)
    return parser


  # action methods ####################################################

  def alloc(self, job, img, config, option={}):
    if option.has_key('n') and int(option['n']) > 0:
        count = int(option['n'])
    else:
        count = 1
    # verify file input
    if not os.path.exists(img):
      print "Error: file "+img+" not found"
      exit(1)
    if not os.path.exists(config):
      print "Error: file "+config+" not found"
      exit(1)
    # absolute paths
    aimg = os.path.abspath(img)
    aconfig = os.path.abspath(config)
    print self.proxy.alloc(job, count, aimg, aconfig, option)

  def clean(self):
    uid = os.geteuid()
    print self.proxy.clean(uid)

  def console(self, nid):
    print self.proxy.console(nid)

  def info(self):
    print self.proxy.info()

  def network(self, option={}):
    uid = os.geteuid()
    print self.proxy.network(uid,option)

  def remove_network(self, net):
    print self.proxy.remove_network(net)

  def remove_node(self, node):
    print self.proxy.remove_node(node)

