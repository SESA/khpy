##########################################
#  Kittyhawk Command-line Interface      #
#   shared definitions                   #
##########################################
import argparse
import copy 

def _ensure_value(namespace, name, value):
    if getattr(namespace, name, None) is None:
        setattr(namespace, name, value)
    return getattr(namespace, name)

def process_input(clinput):
  # call into command function with arguments
  if 'optional_args' in clinput:
    clinput['required_args'].append('optional_args')
  if 'required_args' not in clinput:
    clinput['func']()
  elif len(clinput['required_args']) == 1:
    clinput['func']( clinput[clinput['required_args'][0]] )
  elif len(clinput['required_args']) == 2:
    clinput['func']( clinput[clinput['required_args'][0]], 
        clinput[clinput['required_args'][1]] )
  elif len(clinput['required_args']) == 3:
    clinput['func']( clinput[clinput['required_args'][0]], 
        clinput[clinput['required_args'][1]],
        clinput[clinput['required_args'][2]] )
  elif len(clinput['required_args']) == 4:
    clinput['func']( clinput[clinput['required_args'][0]], 
        clinput[clinput['required_args'][1]],
        clinput[clinput['required_args'][2]],
        clinput[clinput['required_args'][3]] )
  elif len(clinput['required_args']) == 5:
    clinput['func']( clinput[clinput['required_args'][0]], 
        clinput[clinput['required_args'][1]],
        clinput[clinput['required_args'][2]],
        clinput[clinput['required_args'][3]],
        clinput[clinput['required_args'][4]] )
  # follow the above pattern to extend for 6+ parameters

# our custom parameterizers
class KH_store_required(argparse.Action):
  def __call__(self, parser, namespace, values, option_string=None):
    items = copy.copy(_ensure_value(namespace, 'required_args', []))
    items.append(self.dest)
    setattr(namespace, 'required_args', items)
    setattr(namespace, self.dest, values)

class KH_store_optional_const(argparse._StoreConstAction):
  def __call__(self, parser, namespace, values, option_string=None):
    items = copy.copy(_ensure_value(namespace, 'optional_args', {}))
    items[self.dest] = self.const
    setattr(namespace, 'optional_args', items)
    
class KH_store_optional(argparse._StoreAction):
  def __call__(self, parser, namespace, values, option_string=None):
    items = copy.copy(_ensure_value(namespace, 'optional_args', {}))
    items[self.dest] = values
    setattr(namespace, 'optional_args', items)

