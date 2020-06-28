#!/bin/sh
dir=`pwd`
host_ips_file="$dir/ipmi_ip"
function one_node_test()
{
	sh -x   ./ipmi_function.sh  add_bmc_user $2 $3  --ipaddr=$1 --username=usera --userpassword=usera
	sh -x   ./ipmi_function.sh  vnc_config $2 $3  --ipaddr=$1 
	sh -x   ./ipmi_function.sh  mail_alarm $2 $3  --ipaddr=$1 
	sh -x   ./ipmi_function.sh  snmp_alarm $2 $3  --ipaddr=$1 
	sh -x   ./ipmi_function.sh  performance_config $2 $3  --ipaddr=$1 
	#sh -x   ./ipmi_function.sh  boot_set $2 $3  --ipaddr=$1 --boot_type=Bios
	sh -x   ./ipmi_function.sh  boot_set $2 $3  --ipaddr=$1 --boot_type=Uefi
	sh -x   ./ipmi_function.sh  numa_config $2 $3  --ipaddr=$1 
	sh -x   ./ipmi_function.sh  pxe_config $2 $3  --ipaddr=$1 --pxe_device 
	sh -x   ./ipmi_function.sh  alarm_config $2 $3  --ipaddr=$1 
	sh -x   ./ipmi_function.sh  boot_config $2 $3  --ipaddr=$1 
	sh -x   ./ipmi_function.sh  get_sn $2 $3  --ipaddr=$1 
	sh -x   ./ipmi_function.sh  get_mac $2 $3  --ipaddr=$1 
	sh -x   ./ipmi_function.sh  config_raid $2 $3  --ipaddr=$1 --raid_type --disk_list 
	sh -x   ./ipmi_function.sh  power_status $2 $3  --ipaddr=$1 
	sh -x   ./ipmi_function.sh  power_off $2 $3  --ipaddr=$1 
	sh -x   ./ipmi_function.sh  power_on $2 $3  --ipaddr=$1 
	sh -x   ./ipmi_function.sh  hardreset $2 $3  --ipaddr=$1 

}

boot_config()
{
	sh -x   ./ipmi_function.sh  boot_config $2 $3  --ipaddr=$1  --flag_type=set
}


bios_boot()
{
    sh -x   ./ipmi_function.sh  boot_set $2 $3  --ipaddr=$1 --boot_type=Uefi
}



function all_node_test()
{
	host_number=`cat $host_ips_file |wc -l`
    	for((n=1;n<=$host_number;n++))
    	do
            host_ip=`cat $host_ips_file |sed -n "$n"p |awk '{print $1}'`
            admin_name=`cat $host_ips_file |sed -n "$n"p |awk '{print $2}'`
            admin_password=`cat $host_ips_file |sed -n "$n"p |awk '{print $3}'`
           # one_node_test $host_ip $admin_name $admin_password &
		#boot_config  $host_ip $admin_name $admin_password  &
		bios_boot  $host_ip $admin_name $admin_password  &
    	done
}

all_node_test
