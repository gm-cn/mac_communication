#!/bin/sh

log_file="/var/log/cdsstack/supermicro_log"
date_info=`date`
path=`dirname $0`
smc_dir="$path/smc/sum_2.4.0_Linux_x86_64/sum"
smcipmi_dir="$path/smcipmi/SMCIPMITool_2.22.0_build.190701_bundleJRE_Linux_x64/SMCIPMITool"

function_cds_add_bmc_user()
{
    let current_user_num=`$smcipmi_dir $1 $2 $3 user list | grep "Count of currently" | awk '{print $7}'`
    maximum_user_num=`$smcipmi_dir $1 $2 $3 user list | grep "Maximum number of Users" | awk '{print $6}'`
    user_id=`$smcipmi_dir $1 $2 $3 user list | grep "$4" | awk '{print $1}'`
    $smcipmi_dir $1 $2 $3 user list | grep "$4"
    if [[ $? == 0 ]]; then
        $smcipmi_dir $1 $2 $3 user delete $user_id
        $smcipmi_dir $1 $2 $3 user add $user_id $4 $5 2
        #$smcipmi_dir $1 $2 $3 user setpwd $user_id $5 >>$log_file
        if [[ $? == 0 ]]; then
            echo "hostip:$1 $date_info change password success" >> $log_file
        else
            echo "hostip:$1 $date_info change password error" >> $log_file
        fi
    else
        if [[ $current_user_num == $maximum_user_num ]]; then
            echo "hostip:$1 $date_info user full cannot create new user error" >> $log_file
        else
            add=2
            let new_user_slot=$current_user_num+$add
            $smcipmi_dir $1 $2 $3 user add $new_user_slot $4 $5 2
            if [[ $? == 0 ]]; then
                echo "hostip:$1 $date_info add new user $2 password $3 success" >> $log_file
            else
                echo "hostip:$1 $date_info add new user $2 password $3 error" >> $log_file
            fi
        fi
    fi
}

function function_cds_vnc_config()
{
    $smcipmi_dir $1 $2 $3 sol bitrate 115.2
    $smcipmi_dir $1 $2 $3 sol activate | grep "SOL start OK"
    if [[ $? == 0 ]]; then
        echo "hostip:$1 $date_info set vnc success" >> $log_file
    else
        echo "hostip:$1 $date_info set vnc error" >> $log_file
    fi
}

function function_cds_mail_alarm()
{
    $smcipmi_dir $1 $2 $3 ipmi oem x10cfg alert mail 1 baremetal.alarm@capitalonline.net
    $smcipmi_dir $1 $2 $3 ipmi oem x10cfg smtp server 117.79.130.234
    $smcipmi_dir $1 $2 $3 ipmi oem x10cfg smtp server | grep "117.79.130.234"
    if [[ $? == 0 ]]; then
        usleep
    else
        echo "hostip:$1 $date_info set alarm mail error" >> $log_file
    fi
    $smcipmi_dir $1 $2 $3 ipmi oem x10cfg alert mail 1 | grep "baremetal.alarm@capitalonline.net"
    if [[ $? == 0 ]]; then
        echo "hostip:$1 $date_info set alarm mail success" >> $log_file
    else
        echo "hostip:$1 $date_info set alarm mail error" >> $log_file
    fi
}

function function_cds_snmp_alarm()
{
    $smcipmi_dir $1 $2 $3 ipmi lan snmp 1 10.128.101.54
    $smcipmi_dir $1 $2 $3 ipmi lan snmp 1 | grep "10.128.101.54"
    if [[ $? == 0 ]]; then
        echo "hostip:$1 $date_info set snmp alarm success" >> $log_file
    else
        echo "hostip:$1 $date_info set snmp alarm error" >> $log_file
    fi
}

function function_cds_performance_config()
{
    $smc_dir -i $1 -u $2 -p $3 -c GetCurrentBiosCfg --file USER_SETUP.file --overwrite
    cat USER_SETUP.file | grep '<Setting name="Power Technology" selectedOption=' | sed -i '/Setting name="Power Technology" selectedOption=/s/selectedOption=".*"/selectedOption="Energy Efficient" type="Option"/' USER_SETUP.file
    $smc_dir -i $1 -u $2 -p $3 -c ChangeBiosCfg --file USER_SETUP.file  --reboot
    cat USER_SETUP.file | grep '<Setting name="Power Technology" selectedOption=' | grep "Energy Efficient"
    if [[ $? == 0 ]]; then
        echo "hostip:$1 $date_info performance set to Energy Efficient success" >> $log_file
    else
        echo "hostip:$1 $date_info performance set to Energy Efficient error" >> $log_file
    fi

    let count=0
    while [ 1 ]
    do
        if [[ count == 20 ]]; then
            echo "hostip:$1 $date_info performance set to Energy Efficient timeout" >> $log_file
            return 1
        fi
        $smc_dir -i $1 -u $2 -p $3 -c GetCurrentBiosCfg | grep "<Setting name="Power Technology" selectedOption=" | grep "Energy Efficient"
        if [[ $? == 0 ]]; then
            echo "hostip:$1 $date_info performance set to Energy Efficient success" >> $log_file
            return 0
        else
            let count++
        fi
    done
}

function function_cds_boot_set()
{
    if [[ $4 == "UEFI" ]] || [[ $4 == "uefi" ]]; then
        type="UEFI"
    else
        type="LEGACY"
    fi
    $smc_dir -i $1 -u $2 -p $3 -c GetCurrentBiosCfg --file USER_SETUP.file --overwrite
    cat USER_SETUP.file | grep "Boot mode select" | grep "selectedOption" | grep UEFI
    if [[ $? == 0 ]]; then
        boot_mode="UEFI"
    fi

    cat USER_SETUP.file | grep "Boot mode select" | grep "selectedOption" | grep LEGACY
    if [[ $? == 0 ]]; then
        boot_mode="LEGACY"
    fi

    cat USER_SETUP.file | grep "Boot mode select" | grep "selectedOption" | grep DUAL
    if [[ $? == 0 ]]; then
        boot_mode="DUAL"
    fi


    cat USER_SETUP.file | grep "Boot mode select" | sed -i '/Boot mode select/s/'$boot_mode'/'$type'/' USER_SETUP.file
    $smc_dir -i $1 -u $2 -p $3 -c ChangeBiosCfg --file USER_SETUP.file  --reboot
    let count=0
    while [ 1 ]
    do
        if [[ count == 20 ]]; then
            echo "hostip:$1 $date_info set boot type to $type error" >> $log_file
            return 1
        fi
        $smc_dir -i $1 -u $2 -p $3 -c GetCurrentBiosCfg | grep "Boot mode select" | grep $type
        if [[ $? == 0 ]]; then
            echo "hostip:$1 $date_info set boot type to $type success" >> $log_file
            return 0
        else
            let count++
        fi
    done
}

function function_cds_numa_config()
{
    $smc_dir -i $1 -u $2 -p $3 -c GetCurrentBiosCfg --file USER_SETUP.file --overwrite
    cat USER_SETUP.file | grep NUMA | sed -i '/<Setting name="NUMA" select/s/selectedOption=".*"/selectedOption="Enabled" type="Option"/' USER_SETUP.file
    $smc_dir -i $1 -u $2 -p $3 -c ChangeBiosCfg --file USER_SETUP.file  --reboot

    let count=0
    while [ 1 ]
    do
        if [[ count == 20 ]]; then
            echo "hostip:$1 $date_info numa config error" >> $log_file
            return 1
        fi
        $smc_dir -i $1 -u $2 -p $3 -c GetCurrentBiosCfg | grep NUMA | grep Enabled
        if [[ $? == 0 ]]; then
            echo "hostip:$1 $date_info numa config success" >> $log_file
            return 0
        else
            let count++
        fi
    done
}

function function_cds_pxe_config()
{
    $smc_dir -i $1 -u $2 -p $3 -c GetCurrentBiosCfg --file USER_SETUP.file --overwrite
    cat USER_SETUP.file | grep "Ipv4 PXE" | sed -i '/<Steeing name="Ipv4 PXE Support"/s/selectedOption=".*"/selectedOption="Enabled" type="Option"' USER_SETUP.file
    cat USER_SETUP.file | grep "Ipv4 PXE" | grep Enabled
    if [[ $? == 0 ]]; then
        echo "hostip:$1 $date_info set Ipv4 success" >> $log_file
    else
        echo "hostip:$1 $date_info set Ipv4 error" >> $log_file
        return 1
    fi

    cat USER_SETUP.file | grep "Ipv6 PXE" | sed -i '/<Steeing name="Ipv6 PXE Support"/s/selectedOption=".*"/selectedOption="Enabled" type="Option"' USER_SETUP.file
    $smc_dir -i $1 -u $2 -p $3 -c ChangeBiosCfg --file USER_SETUP.file  --reboot
    cat USER_SETUP.file | grep "Ipv6 PXE" | grep Enabled
    if [[ $? == 0 ]]; then
        echo "hostip:$1 $date_info set Ipv6 success" >> $log_file
        return 0
    else
        echo "hostip:$1 $date_info set Ipv6 error" >> $log_file
        return 1
    fi
}

function function_cds_alarm_config()
{
    return function_cds_performance_config
}

function function_cds_boot_config()
{
    $smc_dir -i $1 -u $2 -p $3 -c GetCurrentBiosCfg --file USER_SETUP.file --overwrite
    exchange=`cat USER_SETUP.file | grep 'Boot Option #1" order="1"' | grep -o 'selectedOption=\".*\"'`
    cat USER_SETUP.file | grep "UEFI Network" | sed -i '/order="1"/s/selectedOption=".*"/"$exchange"/' USER_SETUP.file
    cat USER_SETUP.file | grep -w 'Boot Option #1" order="1"' | sed -i '/Boot Option #1" order="1"/s/selectedOption=".*"/selectedOption="UEFI Network" type="Option"/' USER_SETUP.file
    $smc_dir -i $1 -u $2 -p $3 -c ChangeBiosCfg --file USER_SETUP.file  --reboot
    cat USER_SETUP.file | grep -w 'Boot Option #1" order="1"' | grep "Network"
    if [[ $? == 0 ]]; then
        echo "hostip:$1 $date_info boot_config success" >> $log_file
    else
        echo "hostip:$1 $date_info boot_config error" >> $log_file
    fi
}

function function_cds_get_sn()
{
    Service_Tag=`$smcipmi_dir $1 $2 $3 ipmi fru | grep "Product Serial Number" | awk '{print $6}'`
    Firmware_Version=`$smcipmi_dir $1 $2 $3 ipmi ver | grep "IPMI Version" | awk '{print $4}'`
    BIOS_Version=`$smcipmi_dir $1 $2 $3 bios ver | awk '{print $6}'`
    string="$BIOS_Version,$Firmware_Version,$Service_Tag"
	echo $string
}

function function_cds_get_mac()
{
    MAC_address=`$smcipmi_dir $1 $2 $3 ipmi lan mac`
    Service_Tag=`$smcipmi_dir $1 $2 $3 ipmi fru | grep "Product Serial Number" | awk '{print $6}'`
    result1="$Service_Tag \t $MAC_address"
}

function function_cds_config_raid()
{
    return function_cds_performance_config
}

function function_cds_power_status()
{
    status=`$smcipmi_dir $1 $2 $3 ipmi power status |awk '{print $4}' | tr -d "."`
    echo "hostip:$1 $date_info power status:  $status" >> $log_file

}

function function_cds_power_off()
{
    $smcipmi_dir $1 $2 $3 ipmi power down

	ret=`echo $?`
	if [[ $ret != 0 ]];then
		echo "hostip:$1 $date_info power off   error" >> $log_file
		return 0
	fi

	let totle_number=1
	let retry_number=1
	while [ 1 ]
	do
		status=`$smcipmi_dir $1 $2 $3 ipmi power status |awk '{print $4}' | tr -d "."`
		sleep 1
		if [[ "$status" ==  "off" ]];then
		        echo "hostip:$1 $date_info power off success" >> $log_file
	        	break;
		fi

		if [[ $retry == 10 ]];then
			$smcipmi_dir $1 $2 $3 ipmi power down
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
    $smcipmi_dir $1 $2 $3 ipmi power up
    ret=`echo $?`
    if [[ $ret != 0 ]];then
		echo "hostip:$1 $date_info power on   error" >> $log_file
		return 0
	fi
    let totle_number=1
	let retry_number=1
	while [ 1 ]
	do
		status=`$smcipmi_dir $1 $2 $3 ipmi power status |awk '{print $4}' | tr -d "."`
		sleep 1
		if [[ "$status" == "on" ]];then
		        echo "hostip:$1 $date_info power on   success" >> $log_file
	        	break;
		fi

		if [[ $retry == 10 ]];then
			$smcipmi_dir $1 $2 $3 ipmi power up
			let retry=1
		fi

		let retry++
		let totle_number++
		if [[ $totle_number == 200 ]];then
		        echo "hostip:$1 $date_info power on  error" >> $log_file
			break
		fi

	done

}

function function_cds_hardreset()
{
    $smcipmi_dir $1 $2 $3 ipmi power reset
    ret=`echo $?`
	if [[ $ret != 0 ]];then
		echo "hostip:$1 $date_info power reset   error" >> $log_file
		return 0
	fi
        echo "hostip:$1 $date_info power reset   success" >> $log_file

}

function function_cds_change_timezone()
{
    echo "supermicrio does not support change timezone"
    return 0
}

function function_cds_bios_update()
{
	echo "supermicro does not currently support bios update"
}


function function_cds_idrac_update()
{
	echo "supermicro does not currently support idrac update"
}

function function_cds_single_sn()
{
    Service_Tag=`$smcipmi_dir $1 $2 $3 ipmi fru | grep "Product Serial Number" | awk '{print $6}'`
	echo $Service_Tag
}