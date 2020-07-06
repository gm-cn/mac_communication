#!/bin/sh
function usage()
{
    
    echo "ipmi_function version 1.01  Copyright (C) zhaoec(2020-03-02), capitalonline"
    echo "2020-03-02 version 1.01: R540 R640 R740"
    echo "USAGE: $0 [OPTIONS] < add_bmc_user|submit_onetime|vnc_control | bios_update | idrac_update |vnc_config|mail_alarm|snmp_alarm|performance_config|boot_set|numa_config|pxe_config|alarm_config|boot_config|get_sn|single_sn|get_mac|config_raid|power_status|change_timezone|power_off|power_on|hardreset|delete_bmc_user > <password>"
    echo ""
    echo "Available OPTIONS:"
    echo ""
    echo "  --ipaddr       <ipaddr>   ip. "
    echo "  --ip_file      <ip_file>   ip list. "
    echo "  --username     <username>   BMC admin user name "
    echo "  --userpassword <userpassword>   BMC admin password "
    echo "  --boot_type    <boot_type>   BIOS boot type Bios Uefi "
    echo "  --flag_type    <flag_type>   flag type  get set "
    echo "  -h, --help      Show the help message."
    echo "  1 is wrong username "
    echo "  2 is wrong password "
    echo "  3 is wrong ip address "
    echo ""
    echo " compatible bios version including 2.2.11 | 2.5.4"
    echo " compatible idrac version including 3.34.34.34 | 4.10.10.10"
    echo " compatible nics type including 4 nics | 4 nics + 2 sub-nics"
    exit 0
}


function parse_options()
{
    args=$(getopt -o h -l ip_file:,raid_type:,pxe_device:,disk_list:,ipaddr:,username:,userpassword:,boot_type:,update_file:,flag_type:,vnc_password:,help -- "$@")

    if [[ $? -ne 0 ]];then
        usage >&2
    fi

    eval set -- "${args}"

    while true
    do
        case $1 in
            --flag_type)
                flag_type=$2
                shift 2
                ;;
	    --boot_type)
                boot_type=$2
                shift 2
                ;;
            --userpassword)
                userpassword=$2
                shift 2
                ;;
	    --username)
                username=$2
                shift 2
                ;;
            --ipaddr)
                ipaddr=$2
                shift 2
                ;;
            --ip_file)
                ip_file=$2
                shift 2
                ;;
	    --vnc_password)
	        vnc_password=$2
	        shift 2
	        ;;
	    --update_file)
	        update_file=$2
	        shift 2
	        ;;
	    --raid_type)
		raid_type=$2
		shift 2
		;;
	    --pxe_device)
                pxe_device=$2
                shift 2
                ;;
	    --disk_list)
		disk_list=$2
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
    
    if [[ $# -ne 3 ]]; then
        usage
    fi
    action=$1
    name=$2
    password=$3
}


function is_valid_action()
{
    action=$1
    valid_action=(add_bmc_user vnc_control bios_update idrac_update vnc_config mail_alarm submit_onetime snmp_alarm performance_config boot_set numa_config pxe_config alarm_config boot_config get_sn single_sn get_mac config_raid power_status power_off power_on change_timezone hardreset delete_bmc_user)
    for val in ${valid_action[@]}; do
        if [[ "${val}" == "${action}" ]]; then
            return 0
        fi
    done
    return 1
}

parse_options $@

is_valid_action ${action} || echo "invalid action"
path=`dirname $0`

Product_Name=`ipmitool -U $name -P $password -H $ipaddr -I lanplus  fru  |grep "Product Manufacturer" |awk '{print  $4}' `
ipmitool -U $name -P $password -H $ipaddr -I lanplus  fru  |grep "Product Manufacturer" |awk '{print  $4}' |grep Lenovo
if [[ $? == 0 ]]; then
    Product_Name="Lenovo"
fi
ipmitool -U $name -P $password -H $ipaddr -I lanplus chassis power status 1>/dev/null 2>&1

if [[ $? != 0 ]]; then
	echo "username or password not correct error"
	exit 1
fi
case "${Product_Name}" in
    DELL)
        source $path/dell.sh ;;

    Inspur)
        source $path/inspur.sh ;;

    Lenovo)
        source $path/lenovo.sh ;;

    Supermicro)
        source $path/supermicro.sh ;;
    *)
        echo "Unknown Action:${action}!"
	usage
        ;;
esac

case "${action}" in
    add_bmc_user)
	function_cds_add_bmc_user $ipaddr $name $password $username $userpassword $flag_type
        ;;
    vnc_config)
        function_cds_vnc_config $ipaddr $name $password $vnc_password $flag_type
        ;;
    bios_update)
        function_cds_bios_update $ipaddr $name $password $
    	;;
	mail_alarm)
        function_cds_mail_alarm $ipaddr $name $password $flag_type
        ;;
    snmp_alarm)
        function_cds_snmp_alarm $ipaddr $name $password $flag_type
        ;;
    performance_config)
        function_cds_performance_config $ipaddr $name $password $flag_type
        ;;
    boot_set)
        function_cds_boot_set $ipaddr $name $password $boot_type $flag_type
        ;;
    numa_config )
        function_cds_numa_config $ipaddr $name $password $flag_type
        ;;
    pxe_config )
        function_cds_pxe_config $ipaddr $name $password $pxe_device $flag_type
        ;;
    alarm_config)
        function_cds_alarm_config $ipaddr $name $password $flag_type
        ;;
    submit_onetime)
    	function_cds_submit_onetime $ipaddr $name $password $pxe_device $flag_type
        ;;
    vnc_control)
    	function_cds_vnc_control $ipaddr $name $password
        ;;
    boot_config)
        function_cds_boot_config $ipaddr $name $password $flag_type
        ;;
    get_sn)
        function_cds_get_sn $ipaddr $name $password $flag_type
        ;;
    single_sn)
        function_cds_single_sn $ipaddr $name $password $flag_type
        ;;
    get_mac )
        function_cds_get_mac $ipaddr $name $password $flag_type
        ;;
    config_raid)
        function_cds_config_raid $ipaddr $name $password $raid_type $disk_list $flag_type
        ;;
    power_status)
        function_cds_power_status $ipaddr $name $password 
        ;;
    power_off) 
        function_cds_power_off $ipaddr $name $password 
        ;;
    power_on) 
        function_cds_power_on $ipaddr $name $password 
        ;;
    change_timezone)
        function_cds_change_timezone
        ;;
    hardreset)
        function_cds_hardreset $ipaddr $name $password 
        ;;
    delete_bmc_user)
        function_cds_delete_bmc_user $ipaddr $name $password $username $flag_type
        ;;
    *)
        echo "Unknown Action:${action}!"
        usage
        ;;
esac

