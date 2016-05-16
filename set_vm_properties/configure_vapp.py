#!/usr/bin/python

import optparse
from pprint import pprint
import sys
# from pysphere.vi_vapp import VIVApp
from pysphere import VIServer, VITask, MORTypes, VIProperty
from pysphere.resources import VimService_services as VI


# MAIN method
parser = optparse.OptionParser("usage: %prog [options]")
parser.add_option("-s", dest="vcenter", type="string", help="Specify vCenter or Host")
parser.add_option("-u", dest="vcenteruser", type="string", help="specify login")
parser.add_option("-p", dest="vcenterpass", type="string", help="specify password")
parser.add_option("-v", dest="vmName", type="string", help="specify new vm")


options, arguments = parser.parse_args()

print
print 'Begin configuration loop for VM %s' % options.vmName

vapp = {}
newconfig = {
  'add': [],
  'edit': [],
  'remove': []
}

server = VIServer()

print '%s: Connecting to vsphere %s' % (options.vmName,options.vcenter)
server.connect(options.vcenter, options.vcenteruser, options.vcenterpass)
vm = server.get_vm_by_name(options.vmName)

'''
This section enables vApp Options
'''

print '%s: Enabling vApp Options' % options.vmName
request = VI.ReconfigVM_TaskRequestMsg()
_this = request.new__this(vm._mor)
_this.set_attribute_type(vm._mor.get_attribute_type())
request.set_element__this(_this)

spec = request.new_spec()
vappconfig = spec.new_vAppConfig()
vappconfig.set_element_ovfEnvironmentTransport(['com.vmware.guestInfo'])

spec.set_element_vAppConfig(vappconfig)

request.set_element_spec(spec)
task = server._proxy.ReconfigVM_Task(request)._returnval
vi_task = VITask(task, server)

status = vi_task.wait_for_state([vi_task.STATE_SUCCESS,
                                     vi_task.STATE_ERROR])

if status == vi_task.STATE_ERROR:
  print "%s: Error enabling vApp options:" % options.vmName, vi_task.get_error_message()
else:
  print "%s: VM vApp Options enabled" % options.vmName

#
# This section changes vApp properties
#

newconfig = {
    'add':[{'key': 11 , 'id': "custom_ip", 'value':"", 'category':'network_config'},
           {'key': 12 , 'id': "custom_subnet", 'value':"", 'category':'network_config'},
           {'key': 13 , 'id': "custom_gateway", 'value':"", 'category':'network_config'},
           {'key': 14 , 'id': "custom_hostname", 'value':"", 'category':'network_config'},
           {'key': 15 , 'id': "custom_bootproto", 'value':"", 'category':'network_config'},
           {'key': 16 , 'id': "custom_dns1",  'value':"", 'category':'network_config'},
           {'key': 17 , 'id': "custom_dns2", 'value':"", 'category':'network_config'}],
}


request = VI.ReconfigVM_TaskRequestMsg()
_this = request.new__this(vm._mor)
_this.set_attribute_type(vm._mor.get_attribute_type())
request.set_element__this(_this)

spec = request.new_spec()
vappconfig = spec.new_vAppConfig()

properties = []

for operation, items in newconfig.items():
    for item in items:
        prop = vappconfig.new_property()
        prop.set_element_operation(operation)
        if operation == 'remove':
            prop.set_element_removeKey(item)
        else:
            info = prop.new_info()
            for k,v in item.items():
                method = getattr(info, "set_element_" + k)
                method(v)
            prop.set_element_info(info)
        properties.append(prop)

vappconfig.set_element_property(properties)


spec.set_element_vAppConfig(vappconfig)

request.set_element_spec(spec)
task = server._proxy.ReconfigVM_Task(request)._returnval
vi_task = VITask(task, server)

status = vi_task.wait_for_state([vi_task.STATE_SUCCESS,
                                 vi_task.STATE_ERROR])
if status == vi_task.STATE_ERROR:
    print "Error:", vi_task.get_error_message()
else:
    print "VM successfuly reconfigured"

server.disconnect()
