#!/bin/sh

log_file="lenovo_log"
date_info=`date`
path=`dirname $0`
onecli_dir="$path/onecli/onecli"

function_cds_add_bmc_user()
{
    ipmitool_commd="ipmitool -U $2 -P $3 -H $1 -I lanplus"
    	$ipmitool_commd user list | grep "$4"
	if [[ $? == 0 ]]; then
		a=`$ipmitool_commd user list | grep "$4" | awk '{print $1}'`
		$ipmitool_commd  user set password $a $5
		if [[ $? == 0 ]]; then
			echo "host ip: $1 $date_info change password success" >> $log_file
			return 0
		else
			echo "host ip: $1 $date_info change password error" >> $log_file
			return 1
		fi
	else
		for((i=2;i<17;i++));
		do
			$ipmitool_commd user list | sed -n "2,17"p | sed -n "$i,$i"p | grep "NO ACCESS"
			if [[ $? == 0 ]]; then
				$ipmitool_commd  user set name $i $4
        			$ipmitool_commd  user set password $i $5
			        $ipmitool_commd  user priv $i 4 1
        			$ipmitool_commd  user priv $i 4 8
			        $ipmitool_commd  channel  setaccess 1 $i ipmi=on
        			$ipmitool_commd  channel  setaccess 8 $i ipmi=on
			        $ipmitool_commd  user enable $i
				$ipmitool_commd  user list |grep "$4"
			        if [[ $? == 0 ]]; then
                			echo "$date_info add bmc username:$4  password:$5 success" >> $log_file
					return 0
			        else
			                echo "$data_info add bmc username:$4  password:$5 error" >> $log_file
					return 1
			        fi
			fi
		done
	fi
	echo "$data_info add bmc username:$4  password:$5 error user list is full" >> $log_file
	return 1
}

function function_cds_vnc_config()
{
    return function_cds_vnc_config
}

function function_cds_mail_alarm()
{
    $onecli_dir config set IMM.RemoteAlertRecipient_Name.1 "cds-china" --bmc $2:$3@$1
    $onecli_dir config set IMM.remotealertrecipient_email.1 baremetal.alarm@capitalonline.net --bmc $2:$3@$1
    $onecli_dir config set IMM.SMTP_ServerName "117.79.130.234" --bmc $2:$3@$1
    $onecli_dir config show IMM.SMTP_ServerName --bmc $2:$3@$1 | grep "117.79.130.234"
    if [[ $? == 0 ]]; then
        echo "hostip:$1 $date_info email alarm set success" >> $log_file
        return 0
    else
		echo "hostip:$1 $data_info email alarm set error" >> $log_file
        return 1
    fi


}

function function_cds_snmp_alarm()
{
    $onecli_dir config set IMM.SNMPv3_TrapHostname.1 10.128.101.54  --bmc $2:$3@$1
    $onecli_dir config show IMM.SNMPv3_TrapHostname.1 --bmc $2:$3@$1 | grep "10.128.101.54"
    if [[ $? == 0 ]]; then
        echo "hostip:$1 $date_info snmp addr 10.128.101.54 success" >> $log_file
        return 0
    else
		echo "hostip:$1 $data_info snmp snmp addr 10.128.101.54 error" >> $log_file
        return 1
    fi
}

function function_cds_performance_config()
{
    $onecli_dir config set OperatingModes.ChooseOperatingMode "Custom Mode" --bmc $2:$3@$1
    $onecli_dir config set Power.PowerPerformanceBias "Platform Controlled" --bmc $2:$3@$1
    $onecli_dir config set Power.PlatformControlledType "Maximum Performance" --bmc $2:$3@$1
    $onecli_dir config show Power.PlatformControlledType --bmc $2:$3@$1 | grep "Maximum Performance"
    if [[ $? == 0 ]]; then
        echo "hostip:$1 $date_info performance set to Maximum Performance success" >> $log_file
        function_cds_power_off $1 $2 $3
        function_cds_power_on $1 $2 $3
        return 0
    else
		echo "hostip:$1 $data_info performance set to Maximum Performance error" >> $log_file
        return 1
    fi
}

function function_cds_boot_set()
{
    mode=`echo "$4" | tr "A-Z" "a-z"`
    if [[ $mode == bios ]]; then
        $onecli_dir config set BootModes.SystemBootMode "Legacy Mode" --bmc $2:$3@$1
        function_cds_power_off $1 $2 $3
        function_cds_power_on $1 $2 $3
        $onecli_dir config show BootModes.SystemBootMode --bmc $2:$3@$1 | grep "Legacy Mode"
        if [[ $? == 0 ]]; then
            echo "hostip:$1 $date_info boot mode set to bios success" >>$log_file
        else
            echo "hostip:$1 $date_info boot mode set to bios error" >>$log_file
        fi
    else
        $onecli_dir config set BootModes.SystemBootMode "UEFI Mode" --bmc $2:$3@$1
        function_cds_power_off $1 $2 $3
        function_cds_power_on $1 $2 $3
        $onecli_dir config show BootModes.SystemBootMode --bmc $2:$3@$1 | grep "UEFI Mode"
        if [[ $? == 0 ]]; then
            echo "hostip:$1 $date_info boot mode set to UEFI success" >>$log_file
        else
            echo "hostip:$1 $date_info boot mode set to UEFI error" >>$log_file
        fi
    fi
}

function function_cds_numa_config()
{
    $onecli_dir config set Memory.SocketInterleave NUMA  --bmc $2:$3@$1
    $onecli_dir config show Memory.SocketInterleave NUMA --bmc $2:$3@$1 | grep -w "Non-NUMA"
    if [[ $? == 1 ]]; then
        echo "hostip:$1 $date_info set numa success" >> $log_file
        return 0
    else
		echo "hostip:$1 $data_info set numa error" >> $log_file
        return 1
    fi
}

function function_cds_pxe_config()
{
    $onecli_dir config set NetworkBootSettings.UEFIPXEMode.1 enable --bmc $2:$3@$1
    $onecli_dir config set NetworkBootSettings.UEFIPXEMode.2 enable --bmc $2:$3@$1
    $onecli_dir config set NetworkBootSettings.UEFIPXEMode.3 enable --bmc $2:$3@$1
    $onecli_dir config set NetworkBootSettings.UEFIPXEMode.4 enable --bmc $2:$3@$1

    $onecli_dir config set NetworkBootSettings.LegacyPXEMode.1 enable --bmc $2:$3@$1
    $onecli_dir config set NetworkBootSettings.LegacyPXEMode.2 enable --bmc $2:$3@$1
    $onecli_dir config set NetworkBootSettings.LegacyPXEMode.3 enable --bmc $2:$3@$1
    $onecli_dir config set NetworkBootSettings.LegacyPXEMode.4 enable --bmc $2:$3@$1

    $onecli_dir config set NetworkStackSettings.IPv4PXESupport enable --bmc $2:$3@$1

    $onecli_dir config show NetworkStackSettings.IPv4PXESupport --bmc $2:$3@$1 | grep -i enable
    if [[ $? == 0 ]]; then
        echo "hostip:$1 $date_info pxe config   success" >> $log_file
        return 0
    else
        echo "hostip:$1 $date_info pxe config   error" >> $log_file
        return 1
    fi


}

function function_cds_boot_config()
{
    $onecli_dir config set BootOrder.BootOrder Network --bmc $2:$3@$1
    $onecli_dir config show BootOrder.BootOrder | tr "=" " " | awk '{print $2}' | grep -i network
    if [[ $? == 0 ]]; then
        echo "hostip:$1 $date_info boot start with network set success" >> $log_file
        return 0
    else
        echo "hostip:$1 $date_info boot start with network set error" >> $log_file
        return 1
    fi
}

function function_cds_get_sn()
{
    Service_Tag=`$onecli_dir config set SYSTEM_PROD_DATA.SysInfoSerialNum --bmc $2:$3@$1 | grep "SYSTEM_PROD_DATA.SysInfoSerialNum" | tr "=" " "| awk '{print $2}'`
	Firmware_Version=`ipmitool -U $2 -P $3 -H $1 -I lanplus mc info | grep "Firmware Revision" | awk '{print $4}'`
	BIOS_Version=``
	string="$BIOS_Version,$Firmware_Version,$Service_Tag"
	echo $string
}

function function_cds_get_mac()
{
    ipmitool_commd="ipmitool -U $2 -P $3 -H $1 -I lanplus"
    Service_Tag=`$onecli_dir config set SYSTEM_PROD_DATA.SysInfoSerialNum --bmc $2:$3@$1 | grep "SYSTEM_PROD_DATA.SysInfoSerialNum" | tr "=" " "| awk '{print $2}'`
	MAC_address=`$ipmitool_commd lan print | grep -w "MAC Address" | awk '{print $4}'`
	result1="$Service_Tag \t $MAC_address"
	echo -e $result1 >>mac_list.txt
}

function function_cds_config_raid()
{
    return function_cds_performance_config
}

function function_cds_power_status()
{
    ipmitool_commd="ipmitool -U $2 -P $3 -H $1 -I lanplus"
    status=`$ipmitool_commd  power status |awk '{print $4}'`
    echo "hostip:$1 $date_info power status:   $status" >> $log_file
}

function function_cds_power_off()
{
    ipmitool_commd="ipmitool -U $2 -P $3 -H $1 -I lanplus"
    $ipmitool_commd  power off

	ret=`echo $?`
	if [[ $ret != 0 ]];then
		echo "hostip:$1 $date_info power off   error" >> $log_file
		return 0
	fi

	let totle_number=1
	let retry_number=1
	while [ 1 ]
	do
		status=`$ipmitool_commd  power status |awk '{print $4}'`
		sleep 1
		if [[ "$status" ==  "off" ]];then
		        echo "hostip:$1 $date_info power off success" >> $log_file
	        	break;
		fi

		if [[ $retry == 10 ]];then
			$ipmitool_commd  power off
			let retry=1
		fi

		let retry++
		let totle_number++
		if [[ $totle_number == 200 ]];then
		        echo "hostip:$1 $date_info power off error" >> $log_file
			break
		fi

	done
}
function function_cds_power_on()
{
    ipmitool_commd="ipmitool -U $2 -P $3 -H $1 -I lanplus"
    $ipmitool_commd  power on

	ret=`echo $?`
	if [[ $ret != 0 ]];then
		echo "hostip:$1 $date_info power on   error" >> $log_file
		return 0
	fi

	let totle_number=1
	let retry_number=1
	while [ 1 ]
	do
		status=`$ipmitool_commd  power status |awk '{print $4}'`
		sleep 1
		if [[ "$status" ==  "on" ]];then
		        echo "hostip:$1 $date_info power on   success" >> $log_file
	        	break;
		fi

		if [[ $retry == 10 ]];then
			$ipmitool_commd  power on
			let retry=1
		fi

		let retry++
		let totle_number++
		if [[ $totle_number == 200 ]];then
		        echo "hostip:$1 $date_info power on   error" >> $log_file
			break
		fi

	done
}

function function_cds_hardreset()
{
    $onecli_dir misc ospower reboot --bmc $2:$3@$1
	ret=`echo $?`
	if [[ $ret != 0 ]];then
		echo "hostip:$1 $date_info power reset   error" >> $log_file
		return 1
	else
        echo "hostip:$1 $date_info power reset   success" >> $log_file
        return 0
    fi
}

function function_cds_change_timezone()
{
    $onecli_dir config set IMM.TimeZone UTC+8:00  --bmc $2:$3@$1
    if [[ $? == 0 ]]; then
        echo "hostip:$1 $date_info change time zone to UTC+800 success" >> $log_file
        return 0
    else
        echo "hostip:$1 $date_info change time zone to UTC+800 error" >> $log_file
        return 1
    fi
}

function function_cds_bios_update()
{
	echo "lenovo does not currently support bios update"
}


function function_cds_idrac_update()
{
	echo "lenovo does not currently support idrac update"
}

function function_cds_single_sn()
{
    Service_Tag=`$onecli_dir config set SYSTEM_PROD_DATA.SysInfoSerialNum --bmc $2:$3@$1 | grep "SYSTEM_PROD_DATA.SysInfoSerialNum" | tr "=" " "| awk '{print $2}'`
	echo $Service_Tag
}
