#!/bin/bash


usage () {
    echo "USAGE: $0 <dhcp_bridge_name> <dhcp_server_ip> <start_ip> <end_ip>"
    echo ""
    echo "Examples:"
    echo ""
    echo "  dhcp_bridge_name, such as: br1798"
    echo ""
    echo "  dhcp_server_ip, such as: 13.13.13.33/24"
    echo ""
    echo "  start_ip, such as: 13.13.13.100"
    echo ""
    echo "  end_ip, such as: 13.13.13.200"
    echo ""
    exit
}

if [[ $# != 4 ]];then
    usage
fi

DHCP_BRIDGE_NAME=$1
DHCP_NIC_ADDRESS=$2
START_IP=$3
END_IP=$4


function disable_firewall()
{
    state=`firewall-cmd --state`
    if [[ "$state" == "running" ]];then
        systemctl stop firewalld
        systemctl disable firewalld > /dev/null
    else
        echo "====================================================================="
        echo "firewall is stopped and disabled."
    fi
    if [[ "$getenforce" != "Disabled" ]] ;then
        sed -i 's/SELINUX=enforcing/SELINUX=disabled/g' /etc/selinux/config
        setenforce 0
    else
        echo "====================================================================="
        echo "selinux is disabled."
    fi
    iptables -F
    echo "====================================================================="
    echo "disable firewall, selinux, iptables successfully...."
}

function install_package()
{
    echo "====================================================================="
    yum install vim epel-release python2-pip python2 python-devel.x86_64 -y

    mkdir -p ~/.pip
    cat > ~/.pip/pip.conf << EOF
[global]
trusted-host = mirrors.aliyun.com
index-url = https://mirrors.aliyun.com/pypi/simple
EOF
    echo "====================================================================="
    pip install --upgrade pip
    yum -y install syslinux xinetd tftp-server grub2-efi shim dhcp rpcbind nfs-utils ipmitool gcc
}

function config_tftpboot()
{
    IP_ADDRESS=`echo $DHCP_NIC_ADDRESS | awk -F "/" '{print $1}'`
    PREFIX=`echo $DHCP_NIC_ADDRESS | awk -F "/" '{print $2}'`

    echo "====================================================================="
    echo "staring config tftpboot...."

    if [[ ! -d "/tftpboot" ]]; then
        mkdir /tftpboot
    fi
    if [[ ! -d "/tftpboot/deploy_image_template" ]]; then
        mkdir /tftpboot/deploy_image_template
    fi
    cp ./deploy_image/* /tftpboot/deploy_image_template
    sed -i "s/13.13.13.33/$IP_ADDRESS/g"  /tftpboot/deploy_image_template/grub.cfg 

    if [[ ! -d "/tftpboot/pxelinux" ]]; then
        mkdir /tftpboot/pxelinux
    fi
    if [[ ! -d "/tftpboot/pxelinux/default" ]]; then
        mkdir /tftpboot/pxelinux/default
    fi
    if [[ ! -d "/tftpboot/pxelinux/pxelinux.cfg" ]]; then
        mkdir /tftpboot/pxelinux/pxelinux.cfg
    fi
    if [[ ! -d "/tftpboot/user_images" ]]; then
        mkdir /tftpboot/user_images
    fi
    if [[ ! -d "/tftpboot/code" ]]; then
        mkdir /tftpboot/code
    fi
    if [[ ! -d "/tftpboot/log" ]]; then
        mkdir /tftpboot/log
    fi
    cp /usr/share/syslinux/pxelinux.0 /tftpboot/pxelinux
    cp /boot/efi/EFI/centos/shim.efi /tftpboot/pxelinux/bootx64.efi
    cp /boot/efi/EFI/centos/grubx64.efi /tftpboot/pxelinux/grubx64.efi
    cp /tftpboot/deploy_image_template/grub.cfg  /tftpboot/pxelinux/
    cp ./user_image/* /tftpboot/user_images/
    chmod 755 /tftpboot/pxelinux/*.efi
}

function install_tftp()
{
    echo "====================================================================="
    echo "staring install tftp...."

    sed -i '13s/-s \/var\/lib\/tftpboot/-c -v -v -v -v -v --map-file \/tftpboot\/map-file \/tftpboot/g' /etc/xinetd.d/tftp
    sed -i '14s/yes/no/g' /etc/xinetd.d/tftp
    cat > /tftpboot/map-file << EOF
re ^(/tftpboot/) /tftpboot/\2
re ^/tftpboot/ /tftpboot/
re ^(^/) /tftpboot/\1
re ^([^/]) /tftpboot/\1
EOF

    systemctl start xinetd
    systemctl enable xinetd

}


function install_dhcp()
{

    echo "====================================================================="
    echo "staring install dhcp...."

    if [[ -f /etc/dhcp/dhcpd.conf.bak ]];then
        rm -rf /etc/dhcp/dhcpd.conf.bak
    fi
    cp /etc/dhcp/dhcpd.conf /etc/dhcp/dhcpd.conf.bk

    cat > /etc/dhcp/dhcpd.conf << EOF
option space PXE;
option PXE.mtftp-ip    code 1 = ip-address;
option PXE.mtftp-cport code 2 = unsigned integer 16;
option PXE.mtftp-sport code 3 = unsigned integer 16;
option PXE.mtftp-tmout code 4 = unsigned integer 8;
option PXE.mtftp-delay code 5 = unsigned integer 8;
option arch code 93 = unsigned integer 16;

subnet $NETWORK netmask $NETMASK {
    range dynamic-bootp $START_IP $END_IP;
    option subnet-mask $NETMASK;
    default-lease-time 600;
    max-lease-time 7200;
    class "pxeclients" {
        match if substring (option vendor-class-identifier, 0, 9) = "PXEClient";
        next-server $IP_ADDRESS;
        if option arch = 00:07 {
            filename "pxelinux/bootx64.efi";
        } else {
            filename "pxelinux/pxelinux.0";
        }
    }
}
EOF
    echo $DHCP_BRIDGE_NAME >> /etc/sysconfig/dhcpd
    systemctl start dhcpd > /dev/null 2>&1
    systemctl enable dhcpd > /dev/null 2>&1
    echo "install dhcp finished."

}


function config_nfs()
{

    echo "====================================================================="
    echo "staring install nfs...."

    if [[ -f /etc/exports.bak ]];then
        rm -rf /etc/exports.bak
    fi
    cp /etc/exports /etc/exports.bk
    cat > /etc/exports << EOF
/tftpboot/user_images    $NETWORK/$PREFIX(ro,sync,no_root_squash)
/tftpboot/code           $NETWORK/$PREFIX(ro,sync,no_root_squash)
/tftpboot/log            $NETWORK/$PREFIX(rw,sync,no_root_squash)
EOF
    systemctl start rpcbind nfs-server > /dev/null 2>&1
    systemctl enable rpcbind nfs-server > /dev/null 2>&1
}

function main()
{
    disable_firewall
    install_package
    config_tftpboot
    install_tftp
    IP_ADDRESS=`echo $DHCP_NIC_ADDRESS | awk -F "/" '{print $1}'`
    PREFIX=`echo $DHCP_NIC_ADDRESS | awk -F "/" '{print $2}'`
    for line in `ipcalc -pmnb $DHCP_NIC_ADDRESS`
    do
        name=`echo $line | awk -F "=" '{print $1}'`
        value=`echo $line | awk -F "=" '{print $2}'`
        if [[ "$name" = "NETMASK" ]];then
            NETMASK=$value
        elif [[ "$name" = "NETWORK" ]];then
            NETWORK=$value
        fi
    done
    install_dhcp
    config_nfs
}

main

systemctl status xinetd dhcpd rpcbind nfs-server

pip install -r requirements.txt
