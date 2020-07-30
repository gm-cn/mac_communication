#!/bin/bash

# for bare metal interface
# Copyright(C): zhaoercheng, capitalonline

dir=`dirname $0`
if [[ $3 == --* ]]; then
    log_dir="$dir"
else
    log_dir="$3"
fi
host_ips_file="$dir/host_ips"
log_file="$log_dir/network.log"
switch_log_file="$log_dir/auto_switch_crc_log"
mem_log_file="$log_dir/mem.log"
disk_test_log="$log_dir/disk.log"
cpu_log_file="$log_dir/cpu.log"
power_off_log_file="$log_dir/auto_device_status_log"
power_status_log_file="$log_dir/power_status.log"
hardware_all_log="$log_dir/hardware.log"
auto_time=600
wait_time=300
bw=8M

data_path="/data"
password="cds-china"

function usage()
{
    echo "USAGE: $0 [OPTIONS] < rpm-install|crc|fio|nic-down|nic-up|system-device|data-device|final-op|kernel-update|disk_test|switch_crc|mem|scp_hw_test_log|cpu_test|power_status|power_off|check_ssh|hardware_test > <password>"
    echo ""
    echo "Available OPTIONS:"
    echo ""
    echo "  --ipaddr  <ipaddr>      Ip address. Such as: 10.11.11.0/24. "
    echo "  --fix-ip  <fix_ip>      Fix client ip. Such as: 10.10.10.10. "
    echo "  --ip-range  <ip_range>  Ip range. Such as: 10.10.10.10~10.10.10.20. "
    echo "  --nic-name  <nic_name>  Nic name. "
    echo "  --ip_file   <ip_file>   ip list. "
    echo "  --test-type <test_type> test type"
    echo "  -h, --help              Show the help message."
    echo ""
    exit 0
}


function parse_options()
{
    args=$(getopt -o h -l ipaddr:,fix-ip:,ip-range:,nic-name:,test-type:,ip_file:,mem_size:,help -- "$@")

    if [[ $? -ne 0 ]];then
        usage >&2
    fi

    eval set -- "${args}"

    while true
    do
        case $1 in
            --ipaddr)
                ipaddr=$2
                shift 2
                ;;
            --fix-ip)
                fix_ip=$2
                shift 2
                ;;
            --ip-range)
                ip_range=$2
                shift 2
                ;;
            --nic-name)
                nicname=$2
                shift 2
                ;;
            --test-type)
                testtype=$2
                shift 2
                ;;
            --ip_file)
                ip_file=$2
                shift 2
                ;;
	    --mem_size)
                mem_size=$2
                shift 2
                ;;
            -h|--help)
                usage
                ;;
            --)
                shift
                break
                ;;
            *)
                usage
                ;;
        esac
    done

    if [ $# -ne 3 ] && [ $# -ne 2 ]; then
        usage
    fi
    action=$1
    password=$2
}

function is_valid_action()
{
    action=$1
    valid_action=("rpm-install" "crc" "fio" "nic-down" "nic-up" "system-device" "data-device" "final-op" "kernel-update" "disk_test" "switch_crc" "mem" "scp_hw_test_log ""cpu_test" "power_status" "power_off" "check_ssh" "hardware_test")
    for val in ${valid_action[@]}; do
        if [[ "${val}" == "${action}" ]]; then
            return 0
        fi
    done
    return 1
}

parse_options $@

is_valid_action ${action} || usage

sshpass_prefix="sshpass -p $password ssh -o StrictHostKeyChecking=no"
scppass_prefix="sshpass -p $password scp"


case "${action}" in
    crc)
        cdscrc=1 ;;
    fio)
        cdsfio=1 ;;
    mount)
        cdsmount=1 ;;
    nic-down)
        cdsnicdown=1 ;;
    nic-up)
        cdsnicup=1 ;;
    system-device)
        cds_system_device=1 ;;
    data-device)
        cds_data_device=1 ;;
    final-op)
        cds_final_operation=1 ;;
    rpm-install)
	      cds_rpm_install=1 ;;
    kernel-update)
	      cds_kernel_update=1 ;;
    disk_test)
	      cds_disk_test=1 ;;
    switch_crc)
	      cds_switch_crc=1;;
	  scp_hw_test_log)
	      scp_hw_test_log=1;;
    mem)
        cds_mem=1;;
    power_status)
        cds_power_status=1;;
    power_off)
        cds_power_off=1;;
    cpu_test)
	      cds_cpu_test=1;;
    check_ssh)
        cds_check_ssh=1;;
    hardware_test)
	      cds_hardware_test=1;;
    *)
        echo "Unknown Action:${action}!"
        usage
        ;;
esac

function ping_test()
{
	ping $1 -w 2
	return $?
}

function package_install_on_master_node()
{
	yum install expect -y >> /dev/null
	yum install sshpass -y >> /dev/null
	yum install nmap -y >> /dev/null
}


function rpm_install_all_node()
{
	host_number=`cat $host_ips_file |wc -l`

    for((n=1;n<=$host_number;n++))
    do
            host_ip=`cat $host_ips_file |sed -n "$n"p`
            $sshpass_prefix -f $host_ip  "yum install psmisc -y >> /dev/null" &
    done
}

function install_rpm_all()
{
	package_install_on_master_node
	rpm_install_all_node
	sleep 10
}

function get_host_ip()
{
	if [[ $ip_file != "" ]];then
		host_ips_file=$ip_file
	fi
	return 0
	if [[ ! -f $host_ips_file ]]; then
		nmap -sn $ipaddr |grep "Nmap scan report" |awk '{print $5}' > $host_ips_file
	fi
}


function iops_test()
{
	Firmware=`$sshpass_prefix $1 "smartctl  -i /dev/sdb  |grep Firmware " |awk '{print $3}'`
	IOPS_NUM=`$sshpass_prefix  $1 "fio -filename=$2 -direct=1 -iodepth 128 -thread -rw=read  -ioengine=libaio -bs=128k -size=10G -numjobs=1 -runtime=60 -group_reporting -name=read |grep IOPS |cut -d '=' -f 2 |cut -d ',' -f 1"`
	if [[ $IOPS_NUM -eq 0 ]];then
	    echo "host_ip:$1 DEV:$2 FW:$Firmware IOPS:$IOPS_NUM  ERROR" >> $log_file
	else
	    echo "host_ip:$1 DEV:$2 FW:$Firmware IOPS:$IOPS_NUM  SUCCESS" >> $log_file
	fi
}

function get_ips()
{
    ip_list=()
    if [[ $ip_range =~ "~" ]];then
        start_ip=`echo $ip_range | awk -F '~' '{print $1}'`
        end_ip=`echo $ip_range | awk -F '~' '{print $2}'`
        network=`echo $start_ip | awk -F '.' '{printf "%d.%d.%d.",$1,$2,$3}'`
        start_number=`echo $start_ip | awk -F '.' '{print $4}'`
        end_number=`echo $end_ip | awk -F '.' '{print $4}'`
        ip_list=($network$start_number)
        while [ $start_number -lt $end_number ]
        do
            start_number=`expr $start_number + 1`
            ip_list+=( $network$start_number )
        done
    fi
    if [[ -n $fix_ip ]];then
        ip_list+=( $fix_ip )
    fi
    if [[ ${#ip_list[@]} -eq 0 ]];then
        echo "Could not find ip address."
        exit 1
    fi
}

function make_system_device()
{
    $sshpass_prefix $1 \
    "root_part=\`blkid -tLABEL=img-rootfs -odevice\` && \
    devname=\`lsblk -o PKNAME \$root_part | tail -n 1\` && \
    partition_count=\`lsblk -Pbi -o TYPE /dev/\$devname | grep part | wc -l\` && \
    swap_partition_number=\`expr \$partition_count + 1\` && \
    sgdisk -n \$swap_partition_number:0:+128GiB -t \$swap_partition_number:8200 /dev/\$devname > /dev/null && \
    partprobe && \
    udevadm settle && \
    mkswap /dev/\$devname\$swap_partition_number 1>/dev/null 2>&1 && \
    swapon /dev/\$devname\$swap_partition_number && \
    dev_uuid=\`blkid -ovalue /dev/\$devname\$swap_partition_number | head -n 1\` && \
    echo UUID=\$dev_uuid swap swap defaults 0 0 >> /etc/fstab && \
    data_partition_number=\`expr \$swap_partition_number + 1\` && \
    sgdisk -n \$data_partition_number:0:0 -t \$data_partition_number:8300 /dev/\$devname > /dev/null && \
    partprobe && \
    udevadm settle && \
    mkfs.ext4 /dev/\$devname\$data_partition_number -F 1>/dev/null 2>&1 && \
    if [ ! -d /data ] ;then mkdir /data ; fi && \
    mount /dev/\$devname\$data_partition_number /data && \
    dev_uuid=\`blkid -ovalue /dev/\$devname\$data_partition_number | head -n 1\` && \
    echo UUID=\$dev_uuid /data ext4 defaults 0 0 >> /etc/fstab  && echo success || echo failed
    "
}

function make_system_device_all_node()
{
    for host_ip in ${ip_list[@]}
    do
    {
        result=`make_system_device $host_ip`
        if [[ "$result" == "success" ]];then
            echo "host_ip:$host_ip make system device SUCCESS" >> $log_file
        else
            echo "host_ip:$host_ip make system device FAILED" >> $log_file
        fi
    } &
    done
}


function make_data_device()
{
    $sshpass_prefix $1 \
    "if [ ! -d /data$2 ] ;then mkdir /data$2; fi && \
    sgdisk -Z /dev/$3 > /dev/null && \
    mkfs.ext4 /dev/$3 -F 1>/dev/null 2>&1 && \
    mount /dev/$3 /data$2 && \
    dev_uuid=\`blkid -ovalue /dev/$3 | head -n 1\` && \
    echo UUID=\$dev_uuid /data$2 ext4 defaults 0 0 >> /etc/fstab && \
    echo success || echo failed
    "
}


function make_data_device_all_node()
{
	for host_ip in ${ip_list[@]}
	do
	{
        nvme_devices=`$sshpass_prefix $host_ip  "cat /proc/partitions" | grep "nvme*[^p]*$" |gawk '{print $4}' 2>>$log_file`
        let num=1
        for dev in $nvme_devices
        do
        {
            result=`make_data_device $host_ip $num $dev`
            if [[ "$result" == "success" ]];then
                echo "host_ip:$host_ip make data device /dev/$dev SUCCESS"  >> $log_file
            else
                echo "host_ip:$host_ip make data device /dev/$dev FAILED"  >> $log_file
            fi
            num=`expr $num + 1`
         }
        done
	} &
	done
}


function final_operation()
{
    $sshpass_prefix $1 "systemctl stop cloud-init && \
        systemctl stop cloud-init-local && \
        yum remove cloud-init cloud-utils-growpart -y 1>/dev/null 2>&1 && \
        sh /bin/iptables.sh && \
        echo \"su - root -c '/bin/iptables.sh'\" >> /etc/rc.d/rc.local && \
        echo 'route add -net 10.0.0.0/8 gw 10.123.1.254' >> /etc/rc.d/rc.local && \
        route add -net 10.0.0.0/8 gw 10.123.1.254 && \
        echo 'any net 10.0.0.0 netmask 255.0.0.0 gw 10.123.1.254' >>/etc/sysconfig/static-routes && \
        sed  -i 's/GRUB_CMDLINE_LINUX=\"\"/GRUB_CMDLINE_LINUX=\"intel_idle.max_cstate=0 processor.max_cstate=1\"/g' /etc/sysconfig/grub && \
        sed  -i 's/GRUB_CMDLINE_LINUX=\"\"/GRUB_CMDLINE_LINUX=\"intel_idle.max_cstate=0 processor.max_cstate=1\"/g' /etc/default/grub && \
        chmod +x /etc/rc.d/rc.local && grub2-mkconfig -o /boot/grub2/grub.cfg > /dev/null && \
        echo success || echo failed"
}


function final_operation_all_node()
{
    for host_ip in ${ip_list[@]}
    do
    {
        result=`final_operation $host_ip`
        if [[ "$result" == "success" ]];then
            echo "host_ip:$host_ip final operation SUCCESS" >> $log_file
        else
            echo "host_ip:$host_ip final operation FAILED" >> $log_file
        fi
    } &
    done
}

function update_kernel()
{
    $sshpass_prefix $1 "yum install -y wget > /dev/null 2>&1 && \
        wget -O /opt/kernel-3.10.0-514.el7.x86_64.rpm https://buildlogs.centos.org/c7.1611.01/kernel/20161117160457/3.10.0-514.el7.x86_64/kernel-3.10.0-514.el7.x86_64.rpm > /dev/null 2>&1 && \
        yum install /opt/kernel-3.10.0-514.el7.x86_64.rpm -y > /dev/null 2>&1 && \
        grub2-mkconfig -o /boot/grub2/grub.cfg > /dev/null 2>&1 && \
        cp /boot/grub2/grub.cfg /boot/grub2/grub.cfg.bk > /dev/null 2>&1 && \
        sed -i '90,104d' /boot/grub2/grub.cfg > /dev/null 2>&1 && \
        echo success && \
        init 6 || echo failed"
}

function update_kernel_all_node()
{
    for host_ip in ${ip_list[@]}
    do
    {
        result=`update_kernel $host_ip`
        if [[ "$result" == "success" ]];then
            echo "host_ip:$host_ip update kernel SUCCESS" >> $log_file
        else
            echo "host_ip:$host_ip update kernel FAILED" >> $log_file
        fi
    } &
    done
}

function disk_test()
{
	host_number=`cat  $host_ips_file |wc -l`

	for((n=1;n<=$host_number;n++))
	do
		host_ip=`cat  $host_ips_file |sed -n "$n"p`
		nvme_devs=`$sshpass_prefix -f $host_ip  "cat /proc/partitions" | grep "nvme" |gawk '{print $4}'`
		for dev in $nvme_devs
		do
			iops_test $host_ip "/dev/$dev" &
			sleep 1
		done

		sd_devs=`$sshpass_prefix -f $host_ip  "cat /proc/partitions" | grep "sd.*[^1-9]$" |gawk '{print $4}'`
		for dev in $sd_devs
		do
			iops_test $host_ip "/dev/$dev" &
			sleep 1
		done

	done
}


function kill_iperf3()
{
	host_number=`cat $host_ips_file |wc -l`

	for((n=1;n<=$host_number;n++))
	do
		host_ip=`cat $host_ips_file |sed -n "$n"p |awk '{print $2}'`
		$sshpass_prefix -f $host_ip  "killall iperf3" &
	done
}


function iperf3_client()
{
	n=$1
	number=$2
	rw=$3
	ipmi_ip=`cat  $host_ips_file |sed -n "$n"p |awk '{print $1}'`
	ssh_ip=`cat  $host_ips_file |sed -n "$n"p |awk '{print $2}'`
	client_ip=`cat  $host_ips_file |sed -n "$n"p |awk "{print $"$rw"}"`
	service_ip=`cat  $host_ips_file |sed -n "$number"p |awk "{print $"$rw"}"`
	
	ping_test $ssh_ip
	ret=`echo $?`
	if [[ $ret == 1 ]];then

		echo "ipmi_ip:$ipmi_ip  host_ip:$client_ip service_ip:$service_ip  ssh:$ssh_ip No route to host   ERROR" >> $log_file
		return 1
	fi
	
	#Bandwidth=`$sshpass_prefix  $ssh_ip "iperf3 -c $service_ip -t $wait_time -R" |grep sender |awk '{print $7}'`
	local Bandwidth=`$sshpass_prefix  $ssh_ip "iperf3 -c $service_ip -b $bw -t $wait_time -R "|grep sender |awk '{print $7}'`
	eth_info=`$sshpass_prefix  $ssh_ip "ip route" | grep $client_ip |awk -F '[ \t*]' '{print \$3}'`
	crc=`$sshpass_prefix  $ssh_ip "ethtool  -S $eth_info" |grep rx_crc_errors |sed -n 1p|awk '{print $2}'`	
	if [[ $Bandwidth != "" ]]  && [[ "$crc" == "0" ]]; then
		echo "ipmi_ip:$ipmi_ip  host_ip:$client_ip service_ip: $service_ip  Bandwidth:$Bandwidth Gbits/sec CRC:$crc  SUCCESS" >> $log_file
		return 0
	else
		echo "ipmi_ip:$ipmi_ip  host_ip:$client_ip service_ip: $service_ip  Bandwidth:$Bandwidth Gbits/sec CRC:$crc ERROR  " >> $log_file
		return 1
	fi
}

function iperf3_service()
{
	host_number=`cat  $host_ips_file |wc -l`
	row=`cat  $host_ips_file |sed -n 1p |awk '{print NF}'`
	for((j=2;j<=$row;j++))
	do
		for((n=1;n<=$host_number;n++))
        	do
                	host_ip=`cat  $host_ips_file |sed -n "$n"p |awk '{print $2}'`
                	check_ssh $host_ip
			            service=`cat  $host_ips_file |sed -n "$n"p |awk "{print $"$j"}"`
                	$sshpass_prefix -f $host_ip  "iperf3 -s -B $service |grep sender"
                	sleep 1
        	done
	done

}

function crc_test_return() {
    host_number=`cat  $host_ips_file |wc -l`
    row=`cat  $host_ips_file |sed -n 1p |awk '{print NF}'`
    nic_count=`expr $row - 1`
    log_number=`expr $host_number \* $nic_count + 1`
    for ((t=1;t<=100;t++))
    do
      current_log_number=`cat $log_file | wc -l`
      if [[ $current_log_number == $log_number ]];then
        break
      else
        sleep 60
      fi
    done
	  str=""
	  for((i=1;i<=$host_number;i++))
	  do
	    ipmi_ip=`cat  $host_ips_file |sed -n "$i"p |awk '{print $1}'`
	    state=`cat $log_file | grep $ipmi_ip | grep "ERROR"`
      if [[ $state == "" ]];then
        str=$str"{\"ipmi_ip\":""\"$ipmi_ip\""",\"state\":""\"SUCCESS\"}"
      else
        str=$str"{\"ipmi_ip\":""\"$ipmi_ip\""",\"state\":""\"ERROR\"}"
      fi
      if [[  $i != $host_number ]];then
          str=$str","
      fi
    done
    addr=`cat /etc/baremetal-api/baremetal-api.ini | grep -w "scheduler_callback" | grep -E -o "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+:[0-9]+"`
    res=`curl -X POST $addr/bms/v1/task/callback_crc -H 'accept: */*' -H 'Content-Type: application/json' -d '[ '$str' ]'`
}

function scp_hw_test_log() {
  nginx_ip=`cat /etc/baremetal-api/baremetal-api.ini | grep -w "nginx_ip" | grep -E -o "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+"`
  if [[ $1 != "crc" ]];then
    echo -e "================ CPU TEST LOG ==============" > $hardware_all_log
    cat $cpu_log_file >> $hardware_all_log
    echo -e "\n\n================ MEM TEST LOG ==============" >> $hardware_all_log
    cat $mem_log_file >> $hardware_all_log
    echo -e "\n\n================ DISK TEST LOG ==============" >> $hardware_all_log
    cat $disk_test_log >> $hardware_all_log
    echo -e "\n\n================ POWER STATUS TEST LOG ==============" >> $hardware_all_log
    cat $power_status_log_file >> $hardware_all_log
    rm -rf $cpu_log_file $mem_log_file $disk_test_log $power_status_log_file
  fi
  sshpass scp -r -o StrictHostKeyChecking=no $log_dir root@${nginx_ip}:/var/www/log/bms/hardware_log
}

function client_to_service_even()
{
	host_number=`cat  $host_ips_file |wc -l`
	row=`cat  $host_ips_file |sed -n 1p |awk '{print NF}'`
	ip_number=`expr $host_number / 2`

	kill_iperf3
	sleep 10
 
	iperf3_service 
	sleep 10 
	
	for((j=2;j<=$row;j++))
	do
		for((n=1;n<=$ip_number;n++))
		do
			let number=$n+$ip_number
			iperf3_client $n $number $j &
		done

		for((n=$ip_number+1;n<=$host_number;n++))
		do
			let number=$n-$ip_number
			iperf3_client $n $number $j &
		done

	done
	
	sleep $auto_time
	kill_iperf3
}


function client_to_service_odd_one()
{
 	host_number=`cat  $host_ips_file |wc -l`
        row=`cat  $host_ips_file |sed -n 1p |awk '{print NF}'`

        for((j=2;j<=$row;j++))
        do
                n=1
		number=$host_number
		iperf3_client $n $number $j &
		n=$host_number
                number=1
                iperf3_client $n $number $j &
        done


        sleep $auto_time
        kill_iperf3	       
}

function client_to_service_odd()
{
	host_number=`cat  $host_ips_file |wc -l`
        row=`cat  $host_ips_file |sed -n 1p |awk '{print NF}'`
        ip_number=`expr $host_number / 2`

        kill_iperf3
        sleep 10

        iperf3_service
        sleep 10

        for((j=2;j<=$row;j++))
        do
                for((n=1;n<=$ip_number;n++))
                do
                        let number=$n+$ip_number
                        iperf3_client $n $number $j &
                done

                for((n=$ip_number+1;n<=$host_number-1;n++))
                do
                        let number=$n-$ip_number
                        iperf3_client $n $number $j &
                done

        done
	
	sleep $auto_time
	client_to_service_odd_one

        kill_iperf3
}


function nic_down()
{
	$sshpass_prefix  $1  "ifdown $2"
	ret=`echo $?`
	if [[ ret -eq 0 ]];then
        echo "host_ip:$1 ifdown nicname:$2  SUCCESS" >> $log_file
    else
        echo "host_ip:$1 ifdown nicname:$2  ERROR" >> $log_file
    fi
	sleep 1
}

function all_node_nic_down()
{
    host_number=`cat  $host_ips_file |wc -l`

    for((n=1;n<=$host_number;n++))
    do
            host_ip=`cat  $host_ips_file |sed -n "$n"p`
			nic_down $host_ip $nicname & 
    done 
}

function nic_up()
{
	$sshpass_prefix  $1  "ifup $2"
	ret=`echo $?`
	if [[ ret -eq 0 ]];then
        echo "host_ip:$1 ifup nicname:$2  SUCCESS" >> $log_file
    else
        echo "host_ip:$1 ifup nicname:$2  ERROR" >> $log_file
    fi
	sleep 1

}

function all_node_nic_up()
{
        host_number=`cat  $host_ips_file |wc -l`

        for((n=1;n<=$host_number;n++))
        do
                host_ip=`cat  $host_ips_file |sed -n "$n"p`
				nic_up $host_ip $nicname  &
        done 
}

function auto_disk_test_complete()
{
	host_number=`cat  $host_ips_file |wc -l`
	disk_test_number=`cat $disk_test_log |grep "HOST_IP"|wc -l`
	count=1
	while [ 1 ]
	do
		disk_test_number=`cat $disk_test_log |grep "HOST_IP"|wc -l`
		if [[ $host_number == $disk_test_number ]];then
			echo "disk test complete"
			sleep 5
			sync 
			break
		else
			echo "disk test running"
			sleep 3
			let count++
		fi
		if [[ $count == 400 ]];then
			break
		fi
	done
}

function ssh_disk_test()
{
        #sed -i '/'''$1'''/d' /root/.ssh/known_hosts
        check_ssh $1
	if [[ $? != 0 ]]; then
	        return 1
	fi
	$scppass_prefix $dir/auto_disk_test.sh $1:/home/
	sleep 2
	$sshpass_prefix $1  "/home/auto_disk_test.sh $1"
	echo "HOST_IP: $2" >> $disk_test_log
	$sshpass_prefix $1  " cat /home/smartctl_log" >> $disk_test_log
	return 0
}

function auto_disk_test()
{       
        host_number=`cat  $host_ips_file |wc -l`
        echo > $disk_test_log 
        for((n=1;n<=$host_number;n++))
        do  
                host_ip=`cat  $host_ips_file |sed -n "$n"p |awk '{print $1}'`
                ssh_disk_test $host_ip &
        done
	auto_disk_test_complete
}

function auto_switch_test()
{
	host_number=`cat  $host_ips_file |wc -l`
        echo > $switch_log_file  
        for((n=1;n<=$host_number;n++))
        do
                host_ip=`cat  $host_ips_file |sed -n "$n"p`
		$sshpass_prefix $host_ip " display dia | include CRC " >> $switch_log_file 
        done
}
function telnet_crc()
{
	ip=`echo "$1" |awk '{print $1}'`
	user=`echo "$1" |awk '{print $2}'`
	password=`echo "$1" |awk '{print $3}'`
	back="dis dia | include CRC"
	for i in $ip
	do
	{
        	sleep 1
      		echo $user;
        	sleep 1;
        	echo $password;
       	 	sleep 1;
        	echo $back;
        	sleep 1;
        	echo " ";
        	sleep 300;
	}|telnet $i  >"$switch_log_file/$ip" 
	done
}

function auto_telnet_switch_test()
{
        host_number=`cat  $host_ips_file |wc -l`
	mkdir -p $switch_log_file
        for((n=1;n<=$host_number;n++))
        do
                host_ip=`cat  $host_ips_file |sed -n "$n"p`
		telnet_crc "$host_ip" &
        done
}

function mem_test()
{
	#sed -i '/'''$1'''/d' /root/.ssh/known_hosts
	check_ssh $1
	if [[ $? != 0 ]]; then
	        return 1
	fi
	local cpu_number=`$sshpass_prefix $1 "cat /proc/cpuinfo |grep processor |wc -l"`
        local auto_number=$(echo "$cpu_number*0.70"|bc)
        local test_number=`echo $auto_number |cut -d '.' -f 1`
        local mem_total=`$sshpass_prefix $1 "free -g" |grep Mem | awk '{print $2}'`
        local test_mem=$(echo "$mem_total/$test_number"|bc)
        $sshpass_prefix $1 "stress --vm $test_number --vm-bytes "$test_mem"G --vm-hang 100 --timeout $auto_time" &
        sleep $wait_time
        local mem_used=`$sshpass_prefix $1  "free -g" |grep Mem | awk '{print $3}'`
        local mem=$(echo "$mem_used*100/$mem_total"|bc)
        if [ $(echo "$mem > 60"|bc) = 1 ]; then
		echo "host_ip:$2 mem_size:$mem_total mem_used:$mem SUCCESS" >> $mem_log_file
		return 0
	else
		echo "host_ip:$2 mem_size:$mem_total mem_used:$mem ERROR " >> $mem_log_file
		return 1
        fi

}

function auto_mem_test()
{
        host_number=`cat  $host_ips_file |wc -l`
        echo > $mem_log_file
        for((n=1;n<=$host_number;n++))
        do
                host_ip=`cat  $host_ips_file |sed -n "$n"p |awk '{print $2}'`
                ipmi_ip=`cat  $host_ips_file |sed -n "$n"p |awk '{print $1}'`
		mem_test $host_ip $ipmi_ip &
	done
}

function check_ssh()
{
         let count=1
         while [ $count -le 3 ]
         do
                 sleep 2
                 let count++
                 $sshpass_prefix $1 "ls"
                 if [[ $? != 0 ]]; then
                       sed -i '/'''$1'''/d' /root/.ssh/known_hosts
                 else
                         return 0
                 fi
         done
         return 1
}

function test_cpu()
{
        #sed -i '/'''$1'''/d' /root/.ssh/known_hosts
        check_ssh $1
	if [[ $? != 0 ]]; then
	        exit 1
	fi
	local cpu_number=`$sshpass_prefix $1 "cat /proc/cpuinfo |grep processor |wc -l"`
        local auto_number=$(echo "$cpu_number*0.8"|bc)
	local test_number=`echo $auto_number |cut -d '.' -f 1`
        $sshpass_prefix -f $1 "stress -c $test_number -t $auto_time" 
	sleep 10
	local stress_num=`$sshpass_prefix  $1 "ps -ef |grep stress |wc -l"`
        if [[ $stress_num -lt $test_number ]];then
        	$sshpass_prefix -f $1 "stress -c $test_number -t $auto_time"
	fi

	sleep $wait_time
        local cpu_info=`$sshpass_prefix  -t $1 "top -bn1" |grep Cpu`
        local us=`echo "$cpu_info" | awk '{print $2}'`
        local sy=`echo "$cpu_info" | awk '{print $4}'`
        local cpu_use=$(echo "$us+$sy"|bc)
        if [ $(echo "$cpu_use > 50"|bc) == 1 ]; then   
                echo "Hostip:$2 $cpu_info  SUCCESS" >> $cpu_log_file
		return 0
        else
                echo "Hostip:$2 $cpu_info  ERROR" >> $cpu_log_file
		return 1
        fi      	 
}
function auto_cpu_test()
{
        host_number=`cat  $host_ips_file |wc -l`
        echo > $cpu_log_file
        for((n=1;n<=$host_number;n++))
        do
                host_ip=`cat  $host_ips_file |sed -n "$n"p |awk '{print $2}'`
                ipmi_ip=`cat  $host_ips_file |sed -n "$n"p |awk '{print $1}'`
                test_cpu $host_ip $ipmi_ip &
	done   
}

function auto_hardware_test()
{
	host_number=`cat  $host_ips_file |wc -l`
        for((n=1;n<=$host_number;n++))
        do
                host_ip=`cat  $host_ips_file |sed -n "$n"p |awk '{print $2}'`
                ipmi_ip=`cat  $host_ips_file |sed -n "$n"p |awk '{print $1}'`
                hardware_test $host_ip $ipmi_ip &
        done
}
function scp_ipmitool()
{

	$scppass_prefix  /usr/bin/ipmitool $1:/usr/bin/ipmitool
}
function power_status()
{
        local ps_1=`$sshpass_prefix $1 "ipmitool sdr list" |grep "Current 1" | awk '{print $4}'`
        local ps_2=`$sshpass_prefix $1 "ipmitool sdr list" |grep "Current 2" | awk '{print $4}'`
        if [[ "$ps_1" = "no" ]] || [[ "$ps_2" == "no" ]]; then   
                echo "Hostip:$2 mode:A  PS1:$ps_1 PS2:$ps_2  ERROR" >> $power_status_log_file
        else
                echo "Hostip:$2 mode:AB  PS1:$ps_1 PS2:$ps_2  SUCCESS" >> $power_status_log_file
        fi 
}

function hardware_test()
{
    power_status $1 $2
    d=`echo $?`
	ssh_disk_test $1 $2
	a=`echo $?`
	test_cpu $1 $2
	b=`echo $?`
	mem_test $1 $2
	c=`echo $?`
	add=`cat /etc/baremetal-api/baremetal-api.ini | grep -w "scheduler_callback" | grep -E -o "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+:[0-9]+"`
	if [ $a == 0 ] && [ $b == 0 ] && [ $c == 0 ] && [ $d == 0 ]; then
		g="\"$1\""
		d=`curl -X POST $add/bms/v1/task/callback_hard -H 'accept: */*' -H 'Content-Type: application/json' -d '{ "port_ip": '$g', "state": "true"}'`
	else
                f="\"$1\""
		echo $f
		e=`curl -X POST $add/bms/v1/task/callback_hard -H 'accept: */*' -H 'Content-Type: application/json' -d '{ "port_ip": '$f', "state": "false"}'`
		
	fi

}

function auto_power_status()
{
        host_number=`cat  $host_ips_file |wc -l`
        echo > $power_status_log_file
        for((n=1;n<=$host_number;n++))
        do
                host_ip=`cat  $host_ips_file |sed -n "$n"p |awk '{print $1}'`
		scp_ipmitool $host_ip
                power_status $host_ip &
        done    
}

function auto_power_off()
{
        host_number=`cat  $host_ips_file |wc -l`
        echo > $power_off_log_file
        for((n=1;n<=$host_number;n++))
        do
                host_ip=`cat  $host_ips_file |sed -n "$n"p |awk '{print $1}'`
                ping_test $host_ip 
                ret=`echo $?`
                if [[ $ret == 0 ]];then
                        echo "Hostip:$host_ip  SUCCESS" >>  $power_off_log_file
                else
                        echo "Hostip:$host_ip  ERROR" >>  $power_off_log_file
                fi
        done  
}

if [[ ${cds_rpm_install} -eq 1 ]]; then
    install_rpm_all 
fi

if [[ ${cdscrc} -eq 1 ]]; then
	get_host_ip
	dateinfo=`date`
	echo "crc start test $dateinfo"  > $log_file
	host_number=`cat $host_ips_file  |wc -l`
	if test `expr $host_number % 2` == 0 ;then
		client_to_service_even
	else
		client_to_service_odd
	fi
  crc_test_return
  scp_hw_test_log "crc"
fi

if [[ ${cdsfio} -eq 1 ]]; then
	get_host_ip
	dateinfo=`date`
	echo "fio start test $dateinfo"  >> $log_file
	disk_test
fi


if [[ ${cdsnicdown} -eq 1 ]]; then
    get_host_ip
    dateinfo=`date`
    echo "nic down start test $dateinfo"  >> $log_file
    all_node_nic_down
fi


if [[ ${cdsnicup} -eq 1 ]]; then
    get_host_ip
    dateinfo=`date`
    echo "nic up  start test $dateinfo"  >> $log_file
    all_node_nic_up
fi


if [[ ${cds_system_device} -eq 1 ]]; then
    get_ips
    dateinfo=`date`
    echo "make swap and data partition in system device: $dateinfo"  >> $log_file
    make_system_device_all_node
    exit 0
fi


if [[ ${cds_data_device} -eq 1 ]]; then
    get_ips
    dateinfo=`date`
    echo "make data device: $dateinfo"  >> $log_file
    make_data_device_all_node
    exit 0
fi

if [[ ${cds_final_operation} -eq 1 ]]; then
    get_ips
    dateinfo=`date`
    echo "final operation: $dateinfo"  >> $log_file
    final_operation_all_node
    exit 0
fi

if [[ ${cds_kernel_update} -eq 1 ]]; then
    get_ips
    dateinfo=`date`
    echo "kernel update: $dateinfo"  >> $log_file
    update_kernel_all_node
    exit 0
fi

if [[ $cds_disk_test -eq 1 ]]; then
	if [[ $ipaddr == "" ]]; then
		get_host_ip
		auto_disk_test
	else
		ssh_disk_test $ipaddr $fix_ip &
	fi
fi

if [[ $cds_switch_crc -eq 1 ]]; then
        get_host_ip
	auto_telnet_switch_test
fi

if [[ $scp_hw_test_log -eq 1 ]]; then
    scp_hw_test_log $testtype
fi


if [[ $cds_mem -eq 1 ]]; then
        if [[ $ipaddr == "" ]]; then
		get_host_ip
		auto_mem_test
	else
		mem_test $ipaddr $fix_ip &
	fi
fi

if [[ $cds_cpu_test -eq 1 ]];then
	if [[ $ipaddr = "" ]]; then
		get_host_ip
		auto_cpu_test
	else 
		test_cpu $ipaddr $fix_ip &
		
	fi
fi

if [[ $cds_power_status -eq 1 ]];then
	if [[ $ipaddr == "" ]]; then
		get_host_ip
		auto_power_status
	else
		power_status $ipaddr &
	fi
fi

if [[ $cds_power_off -eq 1 ]];then
	get_host_ip
	auto_power_off
fi

if [[ $cds_check_ssh -eq 1 ]];then
	check_ssh $ipaddr
fi

if [[ $cds_hardware_test -eq 1 ]]; then
	if [[ $ipaddr == "" ]]; then
		get_host_ip
		auto_hardware_test
	else	
		hardware_test $ipaddr $fix_ip &
	fi
fi
