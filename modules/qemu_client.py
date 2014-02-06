from kh_client import *
import os
import stat

class QemuClient(KhClient):
  def parse_alloc(self, parser):
    parser.add_argument('-g', action=KH_store_optional_const,
            const=1, help='Enable gdb server')
    return KhClient.parse_alloc(self,parser)
