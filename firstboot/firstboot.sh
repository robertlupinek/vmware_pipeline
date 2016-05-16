#!/bin/bash
#First boot script
#It needs to run from /usr/local/bin

#Attempt to autoconfigure network
/usr/local/bin/configure_network.sh auto

#Disable puppet
systemctl stop puppet
systemctl disable puppet

#Disable first boot
systemctl disable kapsch_firstboot.service
