#!/usr/bin/python

import getopt
import sys
from simple_foreman import simple_foreman

def main():
    # URL to your Foreman server
    url = "https://foreman-staging.staging.local"
    # Default credentials to login to Foreman server
    username = ""
    password = ""
    # Name of the organization to be either created or used
    org = "THEORG"
    #Set up all of the variables to create a host
    hostname = ''
    ip = ''
    hostgroup = '' 
    compute_resource = '' 
    cluster = ''
    power = ''
    hd0_ds = ''
    network_label = ''
    subnet = ''
    test = ''
    delete = ''

    #Text for input errors and help
    input_help =  """Script requires the following format:
        ./mst_create_host.py  \\ 
        --hostname lindev18 \\
        --ip 11.48.191.18 \\ #Optional - set for static IP
        --hostgroup 'MST Base' \\ 
        --compute_profile 2-Medium \\ 
        --compute_resource JC-Midrange"""
    #Attempt to pull in options
    try:
        options, remainder = getopt.getopt(sys.argv[1:], 'o:v', ['hostname=',
                                                                 'ip=',
                                                                 'hostgroup=',
                                                                 'compute_resource=',
                                                                 'cluster=',
                                                                 'hd0_ds=',
                                                                 'power=',
                                                                 'network_label=',
                                                                 'subnet=',
                                                                 'test=',
                                                                 'delete=',
                                                                 'url=',
                                                                 'username=',
                                                                 'password=',
                                                                 ])
    except getopt.GetoptError, e:
        print "Error!  Error! " + str(e)
        print input_help
        sys.exit(1)

    for opt, arg in options:
        if opt in ('--hostname'):
            hostname = arg
        elif opt in ('--ip'):
            ip = arg
        elif opt in '--hostgroup':
            hostgroup = arg
        elif opt in '--compute_resource':
            compute_resource = arg
        elif opt in '--cluster':
            cluster = arg
        elif opt in '--hd0_ds':
            hd0_ds = arg
        elif opt in '--power':
            power = arg
        elif opt in '--network_label':
            network_label = arg
        elif opt in '--subnet':
            subnet = arg
        elif opt in '--test':
            test = arg
        elif opt in '--delete':
            delete = arg
        elif opt in '--url':
            url = arg
        elif opt in '--username':
            username = arg
        elif opt in '--password':
            password = arg

    """Setup api object"""
    sf = simple_foreman( username,password,org,url)

    if test:
      test_result = sf.test_host(hostname,test)
    elif delete == "yes":
      delete_result = sf.delete_host(hostname)
    else:
      """Run method to create the host"""
      new_host = sf.add_host(hostname,ip,org,hostgroup,compute_resource,cluster,hd0_ds,power,network_label,subnet)
      print new_host
      if 'error' in new_host.keys():
        print "ERROR Build failed!"
        print  new_host["error"]["message"]
      else:
        print "Build successfully started for host " + new_host["name"] + "."

if __name__ == "__main__":
    main()
