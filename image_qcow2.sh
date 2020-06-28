function cimage_init()
{
	systemctl disable firewalld
	systemctl disable NetworkManager
	sed -i 's/SELINUX=enforcing/SELINUX=disabled/g' /etc/selinux/config
cat > /etc/sysconfig/modules/8021q.modules << EOF
#! /bin/sh

/sbin/modinfo -F filename 8021q > /dev/null 2>&1
if [ $? -eq 0 ];then
    /sbin/modprobe 8021q
fi
EOF

	chmod 755 /etc/sysconfig/modules/8021q.modules



	yum install cloud-init -y
	systemctl enable cloud-init



	umount  /cloud/
	sed -i '/cloud/d'  /etc/fstab 


	sed -ie 's/^ - resizefs$//' /etc/cloud/cloud.cfg
	sed -ie 's/^ - growpart$//' /etc/cloud/cloud.cfg

	for file in `ls /etc/sysconfig/network-scripts/ifcfg-* | grep -v lo`; do rm -rf $file; done
}

function crate_lable()
{
	fatlabel  /dev/sda3  CONFIG-2
	xfs_admin  -L img-rootfs  /dev/sda5
}

function image_convert_qcow2()
{
	mount  -t  nfs  11.177.178.186:/tftpboot/user_images  /images
	dd if=/dev/sda of=/images/$1 bs=1M count=10240 oflag=direct status=progress
	qemu-img convert -p -t directsync -O qcow2 /images/$1 /images/$2
}


crate_lable
image_convert_qcow2 centos_7.4_bios_10G_64_raw centos_7.4_bios_10G_64
