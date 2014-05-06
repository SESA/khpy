from kh_client import *
import os
import stat

class QemuClient(KhClient):
  def parse_alloc(self, parser):
    parser.add_argument('--iso', action=KH_store_optional_const,
            const=1, help='Load image as an ISO (ignore config)')
    parser.add_argument('-g', action=KH_store_optional_const,
            const=1, help='Enable gdb server')
    parser.add_argument('--vhost', action=KH_store_optional_const,
            const=1, help='spawn vhost enabled server')
    return KhClient.parse_alloc(self,parser)
  def parse_network(self, parser):
    parser.add_argument('--vhost', action=KH_store_optional_const,
            const=1, help='spawn vhost enabled server')
    return KhClient.parse_network(self,parser)
