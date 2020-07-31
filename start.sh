#!/bin/bash

source /config/env
echo "vip of vlan 1800: ${vip1800}"
if [[ ${vip1800} == '' ]]; then
    echo "not found vip of vlan 1800"
    exit 1
fi

mkdir /tftpboot && mount -t nfs -o nolock,vers=3 ${vip1800}:/tftpboot /tftpboot

if [[ $? != 0 ]]; then
  echo "mount ${vip1800}:/tftpboot nfs error"
  exit 1
fi

cat >/etc/rsyncd.conf<<EOF
log file = /var/log/rsyncd.log
uid = root
gid = root
prot = 873
[data]
path = /tftpboot/user_images
read only = no
use chroot=no
EOF

rsync --daemon

PYTHONPATH=${PYTHONPATH}:/app && python -c "from baremetal import bdaemon; bdaemon.main()"