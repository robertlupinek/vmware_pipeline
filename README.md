This project is the combination of several tools with the aim of creating an automated vApp build process.  This project relies on the target VM to be hosted on VMware ESXi.  The vApp properties are set in step 2 are only really helpful for VMware deployment as far as this guy knows. :)

I use these scripts as part of a Jenkins project to create vApps and upload them to our vApp repo.

#1. Foreman - create_host.py is wrapper to provide command line arguments around simple_foreman.py.  

These two script can be used to create a new VM using the Foreman API.  This process can be replaced with any process you have in place to create a template VM.  I use Foreman, but there are many ways to create new VMs.

#2. configure_vapp.py - Use this script to configure the VM created in step 1 as a vApp.  
This leverages the existing VMware Soap API via pysphere.  99% of this is borrowed code.  I am still look for original script to give credit!
  
  I allow the following properties to be set using the configure_vapp.py
  
  custom_ip
  custom_subnet
  custom_gateway
  custom_hostname
  custom_bootproto
  custom_dns1
  custom_dns2

#3.  configure_network.sh and firstboot.sh
What ever process you use to create the VM you will want to be sure to include the configure_network.sh and a first boot scripts to trigger your network configuration.  The configure_network.sh is what I use to automatically configure the network using the `vmtoolsd --cmd='info-get guestinfo.ovfEnv'` command.  You can run the command manually as well. 
  

#4. I also included an example firstboot service for systemd that calls the steps outlined in step 3:


#3. ovftool - OVF tool by vmware is what I have been using to export my VMs to OVAs. 

  Link to ovf tool: https://www.vmware.com/support/developer/ovf/


  ovftool --noSSLVerify --powerOffSource vi://administrator@vsphere.local:$VCENTER_PASS@172.30.8.89/StagingArea/vm/$NEW_HOST $WORKSPACE/$HOSTGROUP.ova

#4. I use the OVF tool to remotely deploy VMs using the OVA we export in step 3.
This gives you the ability to use orchestration tools like ansible to get funky with your deployments.

  https://www.vmware.com/support/developer/ovf/

  ovftool -ds="$DATASTORE" --overwrite --network="$NETWORK_LABEL" --name="$NEW_HOST" --powerOn --powerOffTarget --prop:custom_ip=$NEW_IP\
 --noSSLVerify --prop:custom_subnet=$NEW_SUBNET --prop:custom_gateway=$NEW_GW --prop:custom_hostname=$NEW_HOST\
 --prop:custom_bootproto=$NEW_BOOT_PROTO --prop:custom_dns1=$NEW_DNS_1\
 --prop:custom_dns2=$NEW_DNS_2 $OVA_URL vi://$VMWARE_USER:$VMWARE_PASS@$VCENTER/$DATACENTER/host/$CLUSTER_OR_HOST_NAME/
