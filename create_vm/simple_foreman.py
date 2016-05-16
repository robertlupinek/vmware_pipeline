#!/usr/bin/python
import math
import json
import sys
import ipaddress
import time
try:
    import requests
    requests.packages.urllib3.disable_warnings()
except ImportError:
    print "Please install the python-requests module."
    sys.exit(-1)

class simple_foreman:
    def __init__(self,username,password,org,url):
        self.username = username
        self.password = password
        self.org = org
        self.url = url
        self.foreman_api = "%s/api/v2/" % url
        self.ssl_verify = False
		
    def get_json(self,api_loc):
        try:
            #Performs a GET using the passed URL api_loc
            r = requests.get(api_loc, auth=(self.username, self.password), verify=self.ssl_verify)
        except Exception, e:
            print repr(e)
            sys.exit()
        return r.json()
	
    def post_json(self,api_loc, json_data):
        try:
            #Performs a POST and passes the data to the URL api_loc
            post_headers = {'content-type': 'application/json'}
            result = requests.post(
                api_loc,
                data=json_data,
                auth=(self.username, self.password),
                verify=self.ssl_verify,
                headers=post_headers)
        except Exception, e:
            print repr(e)
            sys.exit()
        return result.json()
	
    def put_json(self,api_loc, json_data):
        try:
            #Performs a POST and passes the data to the URL api_loc
            post_headers = {'content-type': 'application/json'}
            result = requests.put(
                api_loc,
                data=json_data,
                auth=(self.username, self.password),
                verify=self.ssl_verify,
                headers=post_headers)
        except Exception, e:
            print repr(e)
            sys.exit()
        return result.json()
	
    def delete_json(self,api_loc, json_data):
        try:
            #Performs a POST and passes the data to the URL api_loc
            post_headers = {'content-type': 'application/json'}
            result = requests.delete(
                api_loc,
                data=json_data,
                auth=(self.username, self.password),
                verify=self.ssl_verify,
                headers=post_headers)
        except Exception, e:
            print repr(e)
            sys.exit()
        return result.json()

	
    def get_id(self,match_value,api_function):
        #Returns id for mathcing name based on api_function
        return_id = False #Resulting id for search
        #Get json formated data
        data = self.get_json(self.foreman_api + api_function  ) 
        """If you are debugging it might be a good idea to print the
        the contents of the full json formated data returned."""
        #print data 
        #Loop through the results search for the id matching on name provided
        for dict in data['results']:        
            if match_value == dict['name']:
                return_id = dict['id'] 
        #Return the resulting id if one is set
        if return_id:
            return return_id
        else:
            print api_function.upper() + " with a value of '" + match_value + "' was not found."
            sys.exit(-1) 

    def get_compute(self,id):
        #Get json formated data
        api_function = "compute_profiles/"
        data = self.get_json(self.foreman_api + api_function + id  )
        #Return the compute attributes for the compute profile specified
        return data['compute_attributes'][0]['vm_attrs']
    
    def get_data(self,function,id):
        #Get json formated data
        api_function = function 
        data = self.get_json(self.foreman_api + api_function + id  )
        #Return the compute attributes for the compute profile specified
        return data

    def get_subnet(self,ip):
        #Return the subnet name ( should be the VMnetwork name )
        #that the IP Address provided belongs to.
        data = self.get_data("subnets","")
        for subnet in data["results"]:
          try:
            #Convert ip string to IP Address 
            addr4 = ipaddress.ip_address( unicode(ip) )
            #Check to see if the IP Address exists in the subnet
            network = unicode(subnet['network_address'])
            if addr4 in ipaddress.ip_network(network):
              return subnet
          except Exception, e:
            print repr(e)
            print "WARNING: Validate all subnets are configured properly in Foreman."
            print "Make sure they have the proper network address as this is required."
            print "Continuing to search through subnets for IP's Network..."

    def test_host(self,hostname,seconds):
        """This method will check for the status of "No changes".
           If this status is not found in the time specified the script will exit in error.
        """
        status = {}
        seconds = int(seconds)
        loop = True
        while loop:
            #Get the current host status every 10 seconds or when seconds <= 0
            if seconds % 10 == 0 or seconds <= 0:
                status = self.get_json(self.foreman_api + "hosts/" + hostname + "/status" )
                report_status = self.get_json(self.foreman_api + "hosts/" + hostname + "/reports/last" )
            if seconds == -1:
                print "looping forever! Press CTRL+C to exit..."
            if seconds > 0:
                if seconds % 10 == 0:
                  print "looping for another %s seconds..." % ( seconds )
                seconds -= 1
            if status:
                if 'error' in status:    
                    if "Resource host not found by id" in status['error']['message']:
                        print "ERROR: Host, %s, does not exist!" % ( hostname )
                        sys.exit(1)
                        
                if 'status' in status and 'summary' in report_status:    
                    if status['status'] == "No changes" and ( report_status['summary'] == "Success" or report_status['summary'] == "Modified" ) :
                        print "Host, %s, has completed it's build and configuration process." % ( hostname )
                        print "Status: %s Report Summary: %s" % ( status['status'], report_status['summary'] )
                        sys.exit()

            #If still looping sleep for 1 second
            if loop:
                time.sleep(1)
            if seconds == 0:
                print "ERROR: Host did not build in the time specified."
                print "Time specified = %s seconds."  % ( seconds )
                print "Host: %s  Status: %s" % ( hostname, status )
                sys.exit(1)
                loop = False

    def add_host(self,name,ip,org,hostgroup,compute_resource,cluster,hd0_ds,power,network_label,subnet):
        #Gather the numeric ids that represent the parameters requested to configure the server.
        hostgroup_id = self.get_id(hostgroup,"hostgroups")
        #Pull back the dictionary for the hostgroup
        hostgroup_data = self.get_data("hostgroups/",str(hostgroup_id))
        #Setup subnet variables
        subnetname = ""
        subnet_data = {}
        new_host_data = {} 
        new_host = {}
        new_host_dump = {}
        #Setup the dictionary we are using to configure our new host 
        new_host_data = {'host':{
          'managed': True,
          'provision_method': 'build',
          'build': True,
          'name': name,
          'enabled': True,
          'hostgroup_id': hostgroup_id,
        }}

        #Set the subnet and IP address if provided
        if subnet:
          new_host_data['host']['subnet_id'] = self.get_id(subnet,"subnets")
          #If a specific IP address was provided use it.
          if ip:
            #Assign the ip address for the first interface
            new_host_data['host']['ip'] = ip
          subnetname = subnet
        else:
          #Get the subnet based on the IP address requested 
          #Get the subnet name based on the IP or exit with error.
          subnet_data = self.get_subnet(ip)            
          if subnet_data:
            print "Assigning subnet: " + subnet_data['name'] + " to IP address: "  + ip
          else:
            print "No matching subnet was found for IP Address " + ip
            print "Cannot continue build.  Validate subnet for IP provided exists in provisioning tool."
            sys.exit(1)
          #Assign the ip address for the first interface
          new_host_data['host']['ip'] = ip
          #Set the subnet id for the host.
          new_host_data['host']['subnet_id'] = subnet_data['id']
          subnetname = subnet_data['name']
                
        #Assign compute resource if it requested     
        if compute_resource:
            new_host_data['host']['compute_resource_id'] = self.get_id(compute_resource,"compute_resources")
            #Pull the compute attributes defined for the specified compute profile
            compute_attributes = self.get_compute( str( hostgroup_data["compute_profile_id"] ) )
            #Modify the compute attributes after the profile sets this data...
            if cluster:
              compute_attributes['cluster'] = cluster
            #Configure the Virtual NIC(s).
            #If a network label is provided use it vs the subnet name.
            if network_label:
              compute_attributes['interfaces_attributes']['0']['network'] = network_label 
	    else:
	      compute_attributes['interfaces_attributes']['0']['network'] = subnetname 
            #Assign all of the configured compute attributesto the new_host_data 
            new_host_data['host']['compute_attributes'] = compute_attributes
      
        print new_host_data 
        #Convert dict to json object
        new_host_dump = json.dumps(new_host_data) 
        #Attempt to post the new host request:w
        new_host = self.post_json(self.foreman_api + "hosts" ,new_host_dump )

        if "id" in new_host:
            #Attempt to power on the host
            if power == 'on':
              print "Attempting to power on host..."
              new_host_id = str(new_host["id"])
              host_power_on = { "id": new_host_id,"power_action": True }
              new_host_power_state = self.put_json(self.foreman_api + "hosts/"  + new_host_id + "/power" ,json.dumps( { "id": new_host_id,"power_action": "start" } ) )
              print new_host_power_state
        return new_host

    def delete_host(self,hostname):
         #Setup the variables
         api_loc = self.foreman_api + "hosts/" + hostname
         print api_loc
         #Set the error message
         error_message = "ERROR: Host: %s was not deleted successfully." % ( hostname )
         #Attempt to delete the host 
         delete = self.delete_json(api_loc,{}) 
         if "name" in delete:
             print "Host: %s was deleted successfully." % ( hostname )
             sys.exit()
         if "error" in delete:
             if "message" in delete["error"]:
                 #If the host was not found to delete then all is well else error out
                 if "Resource host not found by id " in delete["error"]["message"]:
                     print "Host: %s does not exist." % ( hostname )
                     sys.exit()
                 else:
                     print error_message
                     print delete
                     sys.exit(1)
             #Exit with error if there was message.
             else:
                  print error_message 
                  print delete
                  sys.exit(1)
         #Exit with error if the build did not complete and there was an unexpected result 
         else:
             print error_message 
             print delete
             sys.exit(1)

