from kh_shared import *
import ConfigParser 
import getpass
import random
import string
import time
import xmlrpclib

# Kittyhawk root server object
class KhClient():
  def __init__(self, configsrc):
    self.config = ConfigParser.SafeConfigParser()
    self.config.read(configsrc)
    self.proxy = xmlrpclib.ServerProxy("http://localhost:8000/")

  # Defailt commmand parsers ################################################

  def parse_extras(self, subpar):
    # alloc
    self.parse_alloc(subpar.add_parser('alloc', 
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
      description="Allocate node for a given network"))
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
    # remove
    self.parse_remove(subpar.add_parser('remove',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
      description="Remove network and free allocated nodes"))

  def parse_alloc(self, parser):
    parser.set_defaults(func=self.alloc)
    parser.add_argument('job',type=str,action=KH_store_required, 
      help="Name of user")
    parser.add_argument('img', action=KH_store_required,
        type=str, help='path to application')
    parser.add_argument('config', action=KH_store_required,
        type=str, help='path to configuration')
    parser.add_argument('-n', action=KH_store_optional,
        help='Number of nodes')
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
    parser.add_argument('job', action=KH_store_required,
      help="Name of network")
    parser.set_defaults(func=self.network)
    return parser

  def parse_remove(self, parser):
    # TODO: allow '*' and Net1, Net2...
    parser.add_argument('job', action=KH_store_required,
      help="Name of network")
    parser.set_defaults(func=self.remove)
    return parser

  # action methods ####################################################

  def alloc(self, job, img, config):
    print self.proxy.alloc(job, 1, img, config)

  def clean(self):
    print self.proxy.clean()

  def console(self, nid):
    print self.proxy.console(nid)

  def info(self):
    print self.proxy.info()

  def network(self, name):
    print self.proxy.network(name)

  def remove(self, job):
    print self.proxy.network(job)

