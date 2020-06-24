#!/bin/bash

yum install -y wget > /dev/null 2>&1
wget -O /opt/kernel-3.10.0-514.el7.x86_64.rpm https://buildlogs.centos.org/c7.1611.01/kernel/20161117160457/3.10.0-514.el7.x86_64/kernel-3.10.0-514.el7.x86_64.rpm > /dev/null 2>&1
yum install /opt/kernel-3.10.0-514.el7.x86_64.rpm -y > /dev/null 2>&1
grub2-mkconfig -o /boot/grub2/grub.cfg > /dev/null 2>&1
cp /boot/grub2/grub.cfg /boot/grub2/grub.cfg.bk
sed -i '90,104d' /boot/grub2/grub.cfg
reboot