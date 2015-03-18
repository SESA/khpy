from kh_client import *
import os
import stat

class QemuClient(KhClient):
  def parse_alloc(self, parser):
    parser.add_argument('--ram', action=KH_store_optional, type=int,
        metavar='num', help='Total RAM (GB)')
    parser.add_argument('--cpu', action=KH_store_optional, type=int,
        metavar='num', help='Total CPUs ')
    parser.add_argument("--pin", action=KH_store_optional, type=str,
            metavar="pin", help="Core list for taskset -c (e.g., 1-2,11,12")
    parser.add_argument('--numa', action=KH_store_optional,
            metavar="num", help='NUMA nodes (resources devided evenly)')
    parser.add_argument('--cmd', action=KH_store_optional,
            help='Append string to end of qemu command ')
    parser.add_argument('--perf', action=KH_store_optional,
            default="", help='Enable kvm perf')
    parser.add_argument('--diskimg', action=KH_store_optional_const,
            const=1, help='Load as disk image (ignores config)')
    parser.add_argument('-g', action=KH_store_optional_const,
            const=1, help='Enable gdb server')
    parser.add_argument('-s', action=KH_store_optional_const,
            const=1, help='Signal on termination')
    return KhClient.parse_alloc(self,parser)
