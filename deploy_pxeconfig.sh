#!/bin/bash

# you need to execute it when meet the requirements
# /etc/baremetal-api/baremetal-api.ini already configured
usage () {
    echo "USAGE: $0 <dhcp_server_ip> <callback_ip>"
    echo ""
    echo "Examples:"
    echo ""
    echo "  dhcp_server_ip, such as: 192.168.50.11"
    echo ""
    echo "  callback_ip, such as: 192.168.50.12"
    echo ""
    exit
}

if [[ $# != 2 ]];then
    usage
fi

DHCP_SERVER_IP=$1
CALLBACK_IP=$2

function deploy_pxeagent()
{
    echo "====================================================================="
    echo "git clone pxeagent...."

    if [[ ! -d "/tftpboot/code" ]]; then
        mkdir /tftpboot/code
    fi
    if [[ ! -d "/tftpboot/log" ]]; then
        mkdir /tftpboot/log
    fi
    cat > /tftpboot/code/boot_pxeagent.sh << EOF
custom_image=""
if [[ \$custom_image == "" ]]; then
    cp -rf /code/pxe_agent /usr/share/pxe_agent
else
    cp -rf /code/pxe_agent_custom /usr/share/pxe_agent
fi
AGENTDIR=/usr/share/pxe_agent
sleep 10
sh \$AGENTDIR/install.sh
EOF
    chmod 777 /tftpboot/code/boot_pxeagent.sh

    if [[ ! -d "/tftpboot/code/pxe_agent" ]]; then

        git clone https://cdsdevops:cds-china%402019@repos.capitalonline.net/baremetal/pxe_agent.git /tftpboot/code/pxe_agent
    fi
}

function generate_pxeconfig() {

    echo "====================================================================="
    echo "generate pxe default config...."

    if [[ ! -d "/tftpboot/pxelinux/instances/default" ]]; then
        mkdir -p /tftpboot/pxelinux/instances/default
    fi

    if [[ -f /tftpboot/deploy_image_template/deploy_ramdisk ]]; then
        cp /tftpboot/deploy_image_template/deploy_ramdisk /tftpboot/pxelinux/instances/default
        cp /tftpboot/deploy_image_template/deploy_kernel /tftpboot/pxelinux/instances/default
    else
        echo 'the template of deploy images are not in the directory of /tftpboot/deploy_image_template'
    fi


    cat > /tftpboot/pxelinux/grub.cfg << EOF
set default="0"
set timeout=3
set hidden_timeout_quiet=false

menuentry "deploy" {
        linuxefi deploy_image_template/deploy_kernel rw selinux=0 scheduler-callback=http://$CALLBACK_IP:7070/bms/v1/task/pxe/notify user-image-nfs-path=$DHCP_SERVER_IP:/tftpboot/user_images
        initrdefi deploy_image_template/deploy_ramdisk
}
EOF
    cat > /tftpboot/pxelinux/pxelinux.cfg/default << EOF
default deploy

label deploy
    kernel instances/default/deploy_kernel
    append initrd=instances/default/deploy_ramdisk  rw selinux=0 scheduler-callback=http://$CALLBACK_IP:7070/bms/v1/task/pxe/notify user-image-nfs-path=$DHCP_SERVER_IP:/tftpboot/user_images
EOF

}

function main()
{
    deploy_pxeagent
    generate_pxeconfig
}

main
