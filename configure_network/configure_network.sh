#!/bin/bash

#################################
#Description: 
# This script is used to run post deployment configuration for VM's 
# This script will have the ability to auto configure network interfaces or allow the user to select
# the network interface they wish to configure.
#Last Modfied:
# Robert Lupinek 4/22/2016
#
function get_release_version() {
	#Set the release_major and release_minor variables
	release_major=`lsb_release -a | grep Release | awk '{ print $2  }' | awk -F. '{ print $1 }'`
	release_minor=`lsb_release -a | grep Release | awk '{ print $2  }' | awk -F. '{ print $2 }'`
	echo "Major Release: $release_major  Minor Release: $release_minor"
}

#Archive existing network interfaces
function archive_network_scripts() {
    #Archive existing network interface scripts
    cd /etc/sysconfig/network-scripts
    #Create the archive directory if it does not exist
    [ ! -d /etc/sysconfig/network-scripts/archive ] && mkdir /etc/sysconfig/network-scripts/archive
    #Archive all existing interfaces that are not the loop back.
    for config_file in `ls ifcfg-*`
    do
        if [ "$config_file" == "ifcfg-lo" ]
        then
            echo "This ( $config_file )is the config for loop back.  Do not mess with this one."
        else
            echo "This ( $config_file ) is being archived in /etc/sysconfig/network-scripts/archive."
			echo yes | mv -f $config_file /etc/sysconfig/network-scripts/archive/
		fi
	done
}

#Gather variables for existing interfaces
function gather_interfaces() {
	#We are only looking for interfaces that are up
	up_interfaces=$( ip -o link show | grep -v virbr0 | awk '{if ( $9 == "UP"){ print $2}  }' | sed 's/://') 
	echo $up_interfaces
}


function create_interface() {

    custom_bootproto=$1   
    custom_device=$2
    custom_hwaddr=$3
    custom_nm=$4
    custom_ip=$5
    custom_subnet=$6
    custom_gateway=$7
    custom_hostname=$8
    custom_dns1=$9
    custom_dns2=${10}


    if [ "$custom_bootproto" == "DHCP" ]
    then
        #Log output
        logger -s "$0: Creating network interface $custom_device configured for DHCP."
        #Create the config file
        cat > /etc/sysconfig/network-scripts/ifcfg-$custom_device <<EOF
#Config created using configure_network.sh
BOOTPROTO=$custom_bootproto
DEVICE=$custom_device
HWADDR=$custom_hwaddr
ONBOOT=yes
NM_CONTROLLED=$custom_nm
EOF

    else
	#Log output
        logger -s "$0: Creating network interface $custom_device with IP address of $custom_ip."
	#Create the config file
        cat > /etc/sysconfig/network-scripts/ifcfg-$custom_device <<EOF
#Config created using configure_network.sh
BOOTPROTO=$custom_bootproto
DEVICE=$custom_device
HWADDR=$custom_hwaddr
IPADDR=$custom_ip
NETMASK=$custom_subnet
GATEWAY=$custom_gateway
ONBOOT=yes
NM_CONTROLLED=$custom_nm
PEERDNS=yes
PEERROUTES=yes
DNS1=$custom_dns1
DNS2=$custom_dns2
EOF

    fi
}

#Autoconfigure network interface based on vAPP properties
function vmware_auto_configure_net() {

    #This function attempts to create a 
	if [ $(which vmtoolsd) ]
	then
		#Get the network properties IF they were set during OVA deployment
		custom_device=$(gather_interfaces | awk '{ print $1 }')
		custom_hwaddr=$( ip addr show dev $custom_device | grep link/ether | awk '{ print $2}' )
		custom_ip=$(vmtoolsd --cmd='info-get guestinfo.ovfEnv' | grep custom_ip | awk -F'"' '$0=$4')
		custom_subnet=$(vmtoolsd --cmd='info-get guestinfo.ovfEnv' | grep custom_subnet | awk -F'"' '$0=$4')
		custom_gateway=$(vmtoolsd --cmd='info-get guestinfo.ovfEnv' | grep custom_gateway | awk -F'"' '$0=$4')
		custom_hostname=$(vmtoolsd --cmd='info-get guestinfo.ovfEnv' | grep custom_hostname | awk -F'"' '$0=$4')
		custom_dns1=$(vmtoolsd --cmd='info-get guestinfo.ovfEnv' | grep custom_dns1 | awk -F'"' '$0=$4')
		custom_dns2=$(vmtoolsd --cmd='info-get guestinfo.ovfEnv' | grep custom_dns2 | awk -F'"' '$0=$4')
		custom_bootproto=$(vmtoolsd --cmd='info-get guestinfo.ovfEnv' | grep custom_bootproto | awk -F'"' '$0=$4')
                custom_nm='no'
	
		#Make sure variables are set before auto configuring the network interfaces.
		if [ ! -z "$custom_device" ] && [ ! -z "$custom_ip" ] && [ ! -z "$custom_subnet" ] && [ ! -z "$custom_gateway" ] && [ ! -z "$custom_hostname" ] && [ ! -z "$custom_bootproto" ]
		then 
                    #Archive old network scripts
		    archive_network_scripts
		    
                    #Create the new interface file
		    

                    create_interface $custom_bootproto $custom_device $custom_hwaddr $custom_nm $custom_ip $custom_subnet $custom_gateway $custom_hostname $custom_dns1 $custom_dns2 
		    #Configure hostname
                    set_hostname $custom_hostname $custom_ip
		    #Restart network services
		    restart_networking 

		else
			echo "Missing vApp properties.  Cannot auto configure network based on vAPP Properties."
			exit 1
		fi
	else
		echo "Missing vmtoolsd.  Cannot auto configure network based on vAPP Properties."
		exit 1
	fi
}

#Restart networking
function restart_networking() {
	service network restart
}

function set_hostname() {

    get_release_version

    new_hostname=$1
    new_shortname=$(echo $new_hostname | awk -F. '{print $1 }' )
    new_ip=$2
    
    #Set the hostname using the hostnamectl command if RHEL 7
    if [ $release_major == "7" ]
    then
        hostnamectl set-hostname $new_hostname --static 
    fi

    #Add the entry for the hostname in the network script
    sed -i "/HOSTNAME/d" /etc/sysconfig/network
    echo "HOSTNAME=$new_hostname" >> /etc/sysconfig/network

    #Configure etc hosts
    #Remove the host from the /etc/hosts file if it exists
    sed -i "/$new_hostname/d" /etc/hosts
    #Add the host to the host file
    echo "$new_ip   $new_hostname $new_shortname" >> /etc/hosts
   

}

function valid_ip()
{
    ip=$1

    if [[ $ip =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        echo "success"
    else
       echo "fail"
    fi
}



#Manual Configure network settings
function manual_configure_network() {
    #Create the interface selection screen
    #We only display interfaces that are up...
    interface=""
    selection=""
    custom_bootproto=""
   
    build_menu "$(gather_interfaces )" "Please make a selection and press ENTER: " "Please select the network interface you wish to configure: "  
    custom_device=$result
    build_menu "Static DHCP" "Please make a selection and press ENTER: " "Please select the configuration mode for the interface ( DHCP = automatic where available ): "
    custom_bootproto=$result
    echo "interface: " $custom_device " bootproto: " $custom_bootproto 
    #Assigning the mac address
    custom_hwaddr=$( ip addr show dev $custom_device | grep link/ether | awk '{ print $2}' )
    
    #If the bootproto is DHCP we have enough information to create the interface 
    if [ "$custom_bootproto" == "DHCP" ]
    then
        #Create a DHCP style network interface
        echo "Creating DHCP enabled network interface for $custom_device."
	#Archive old network scripts
        archive_network_scripts
        custom_nm="yes"
        create_interface $custom_bootproto $custom_device $custom_hwaddr $custom_nm
        #Restart network services
        restart_networking

    else #Static Build
        custom_bootproto='none'
        custom_nm="no"
        options="HOSTNAME IP SUBNET GATEWAY DNS1 DNS2 Save_Apply Quit"
        PS3=$2
        message=$3
        result=""
        while [ "$result" == "" ] ; do
            clear
            #echo BOOTPROTO=$custom_bootproto
            echo "DEVICE:      $custom_device"
            echo "MAC ADDRESS: $custom_hwaddr"
            echo "-------------------------"
            echo "Hostname: $custom_hostname"
            echo "IP:       $custom_ip"
            echo "SUBNET:  $custom_subnet"
            echo "GATEWAY:  $custom_gateway"
            echo "DNS1:     $custom_dns1"
            echo "DNS2:     $custom_dns2"

            select selection in $options; do
                    if [ "$selection" == "" ]; then
                            echo "Please enter a valid number. Retry."
                    else
                        if [ "$selection" == "Quit" ]
                        then
                            echo "$selection was selected"
                            exit
                        elif [ "$selection" == "IP" ]
                        then
                            echo "Enter IP ( Example: 172.40.20.50 ):"
                            read custom_ip 
			    if [ $(valid_ip $custom_ip) == "fail" ]
			    then 
				echo "Please enter a valid IP.  Press ENTER to continue.";read
				custom_ip=""
			    fi
                        elif [ "$selection" == "SUBNET" ]
                        then
                            echo "Enter Subnet ( Example: 255.255.255.0 ):"
                            read custom_subnet 
                            if [ $(valid_ip $custom_subnet) == "fail" ]
                            then
                                echo "Please enter a valid IP.  Press ENTER to continue.";read
                                custom_subnet=""
                            fi

                        elif [ "$selection" == "GATEWAY" ]
                        then
                            echo "Enter Gateway ( Example: 172.40.20.1 ):"
                            read custom_gateway 
                            if [ $(valid_ip $custom_gateway ) == "fail" ]
                            then
                                echo "Please enter a valid IP.  Press ENTER to continue.";read
                                custom_gateway=""
                            fi

                        elif [ "$selection" == "DNS1" ]
                        then
                            echo "Enter DNS1 ( Example: 8.8.8.8 ):"
                            read custom_dns1 
                            if [ $(valid_ip $custom_dns1) == "fail" ]
                            then
                                echo "Please enter a valid IP.  Press ENTER to continue.";read
                                custom_dns1=""
                            fi

                        elif [ "$selection" == "DNS2" ]
                        then
                            echo "Enter DNS2 ( Example: 8.8.8.8 ):"
                            read custom_dns2 
                            if [ $(valid_ip $custom_dns2) == "fail" ]
                            then
                                echo "Please enter a valid IP.  Press ENTER to continue.";read
                                custom_dns2=""
                            fi

                        elif [ "$selection" == "HOSTNAME" ]
                        then
                            echo "Enter Hostname:"
                            read custom_hostname 
                        elif [ "$selection" == "Save_Apply" ]
                        then
                            #Build the interface configuration script and exit menu
                            #Make sure the needed variables are set...
                            if [ ! -z "$custom_device" ] && [ ! -z "$custom_hwaddr" ] && [ ! -z "$custom_nm" ] && [ ! -z "$custom_ip" ] && [ ! -z "$custom_subnet" ] && [ ! -z "$custom_gateway" ] && [ ! -z "$custom_hostname" ] && [ ! -z "$custom_bootproto" ]
                            then
                                #Archive old network scripts
                                archive_network_scripts
                                #Create the interface file
                                create_interface $custom_bootproto $custom_device $custom_hwaddr $custom_nm $custom_ip $custom_subnet $custom_gateway $custom_hostname $custom_dns1 $custom_dns2
                                #Set the hostname
                                set_hostname $custom_hostname $custom_ip
				#Restart network services
                    		restart_networking

                                result=$selection
                            else
                                echo "You are missing some parameters.  The only optional paramters are the DNS1 and DNS2 options."
                                echo "Press enter..."
                                read
                            fi
                        fi
                    fi
                    break
            done
        done
    fi
    exit 0
}

function build_menu() {
    #This function builds a menu selecting options returned in the variable $result
    options=$1
    PS3=$2
    message=$3
    result=""
    while [ "$result" == "" ] ; do
        clear
        echo $message
        select selection in $options "Exit"; do
                if [ "$selection" == "" ]; then
                        echo "Please enter a valid number. Retry."
                else
                        if [ "$selection" == "Exit" ]
                        then
                            echo "$selection was selected"
                            exit
                        else
                            echo "$selection was selected."
                            result=$selection
                        fi

                fi
                break
        done
    done

}

#Make sure an argument was provided
if [ ! -z $1 ]
then
  if [ $1 == "auto" ]
  then
    #Auto generate new config
    vmware_auto_configure_net
  elif [ $1 == "manual" ]
  then
    #Manually configure the network interface
    manual_configure_network
  elif [ $1 == "archive" ]
  then
    #Archive existing network interfaces
    archive_network_scripts
  else
    echo "Please specify auto or maunual config:"
    echo "  configure_network.sh auto"
    echo "  configure_network.sh maunual"
    echo "  configure_network.sh archive"
  fi
else
  echo "Please specify auto , maunual, or achive config:"
  echo "  configure_network.sh auto"
  echo "  configure_network.sh maunual"
  echo "  configure_network.sh archive"
fi
