#!/bin/sh
log_file="huawei_log"
date_info=`date`
cmd_dir="/root/bin/urest"
update_file_path="/tftpboot/update_file/"

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
    ipmitool_commd="ipmitool -U $2 -P $3 -H $1 -I lanplus"
	$ipmitool_commd sol payload enable 1 2
	$ipmitool_commd sol payload enable 8 2
    $ipmitool_commd sol set volatile-bit-rate 115.2
    $ipmitool_commd sol set non-volatile-bit-rate 115.2
    $ipmitool_commd sol info |grep  115.2
	if [[ $? == 0 ]]; then
        echo "$date_info set sol bit rate 115.2  success" >> $log_file
    else
        echo "$data_info set sol bit rate 115.2  error" >> $log_file
    fi
    #$ipmitool_commd sol activate  <  ~?
}

function function_cds_mail_alarm()
{
    ./urest -H 192.17.1.63 -U Administrator -P 123cpucpu@ request -I /redfish/v1/Managers/1/SmtpService -T PATCH -B smtp.json
    #{
    #    "ServiceEnabled": true,
    #    "ServerAddress": "117.79.130.234",
    #    "TLSEnabled": true,
    #    "AnonymousLoginEnabled": false,
    #    "AlarmSeverity": "Critical",
    #    "RecipientAddresses":[{
    #        "Enabled": true,
    #        "EmailAddress": "baremetal.alarm@capitalonline.net"
    #    }]
    #
    #}

}

function function_cds_snmp_alarm()
{
    sshpass_prefix="sshpass -p $3 ssh $2@$1"
    $sshpass_prefix "ipmcset -t trap -d state -v enabled"
    $sshpass_prefix "ipmcset -t trap -d version -v V2C"
    $sshpass_prefix "ipmcset -t trap -d address -v 1 10.128.101.54"
}

function function_cds_performance_config()
{
    urset_comm="$cmd_dir -H $1 -U $2 -P $3"
    $urset_comm setbios -A CustomPowerPolicy -V Performance
}

function function_cds_boot_set()
{
    urset_comm="$cmd_dir -H $1 -U $2 -P $3"
    if [[ $4 == "Bios" ]]; then
        $urset_comm setbios -A BootType -V LegacyBoot
    else
        $urset_comm setbios -A BootType -V UEFIBoot
    fi
    function_cds_power_off $1 $2 $3
    function_cds_power_on $1 $2 $3
    $urset_comm getbiosdetails -A BootType
}

function function_cds_numa_config()
{
    urset_comm="$cmd_dir -H $1 -U $2 -P $3"
    $urset_comm setbios -A NUMAEn -V Enabled
}

function function_cds_pxe_config()
{
    urset_comm="$cmd_dir -H $1 -U $2 -P $3"
    $urset_comm setbios -A PXE1Setting -V Enabled
    $urset_comm setbios -A PXE2Setting -V Enabled
    $urset_comm setbios -A PXE3Setting -V Enabled
    $urset_comm setbios -A PXE4Setting -V Enabled
    function_cds_power_off $1 $2 $3
    function_cds_power_on $1 $2 $3
    $urset_comm getbiosdetails -A PXE1Setting
    $urset_comm getbiosdetails -A PXE2Setting
    $urset_comm getbiosdetails -A PXE3Setting
    $urset_comm getbiosdetails -A PXE4Setting
}

function function_cds_alarm_config()
{
    return function_cds_alarm_config
}

function function_cds_boot_config()
{
    sshpass_prefix="sshpass -p $3 ssh $2@$1"
    $sshpass_prefix "ipmcset -d bootdevice -v 1 permanent"
}

function function_cds_get_sn()
{
    sshpass_prefix="sshpass -p $3 ssh $2@$1"
    a=`$sshpass_prefix "ipmcget -d serialnumber"`
    Service_Tag=`echo $a | tr ":" " " | awk '{print $4}' | tr "\n" "\t"`
	BIOS_Version=`$sshpass_prefix "ipmcget -d version" | grep BIOS | tr ")" " " | awk '{print $4}'| tr "\n" "\t"`
	Firmware_Version=`$sshpass_prefix "ipmcget -d version" | grep "Active iBMC"| grep Version | tr ")" " " | awk '{print $5}'| tr "\n" "\t"`
	string="$BIOS_Version,$Firmware_Version,$Service_Tag"
	echo $string
}

function function_cds_get_mac()
{
	sshpass_prefix="sshpass -p $3 ssh $2@$1"
    mac1=`$sshpass_prefix "ipmcget -d macaddr" | grep LOM | grep Port1 | awk '{print $5}'| tr "\n" "\t"`
    mac2=`$sshpass_prefix "ipmcget -d macaddr" | grep LOM | grep Port2 | awk '{print $5}'| tr "\n" "\t"`
    mac3=`$sshpass_prefix "ipmcget -d macaddr" | grep LOM | grep Port3 | awk '{print $5}'| tr "\n" "\t"`
    mac4=`$sshpass_prefix "ipmcget -d macaddr" | grep LOM | grep Port4 | awk '{print $5}'| tr "\n" "\t"`
	echo "mac address is $mac1,$mac2,$mac3,$mac4"
	return 0
}

function function_cds_config_raid()
{
    urset_comm="$cmd_dir -H $1 -U $2 -P $3"
    $urset_comm addvdisk -I 0 -DI 0 1 -VL RAID1
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
    ipmitool_commd="ipmitool -U $2 -P $3 -H $1 -I lanplus"
    $ipmitool_commd  power reset

	ret=`echo $?`
	if [[ $ret != 0 ]];then
		echo "hostip:$1 $date_info power reset   error" >> $log_file
		return 0
	else
        echo "hostip:$1 $date_info power reset   success" >> $log_file
    fi
}

function function_cds_change_timezone()
{
    sshpass_prefix="sshpass -p $3 ssh $2@$1"
    $sshpass_prefix "ipmcset -d timezone -v Asia/Shanghai"
}

function function_cds_bios_update()
{
	echo "huawei does not currently support bios update"
}


function function_cds_idrac_update()
{
	echo "huawei does not currently support idrac update"
}

function function_cds_single_sn()
{
    sshpass_prefix="sshpass -p $3 ssh $2@$1"
    a=`$sshpass_prefix "ipmcget -d serialnumber"`
    sn=`echo $a | tr ":" " " | awk '{print $4}'`
	echo $sn
}

function function_cds_vnc_control()
{
	echo "huawei does not support vnc"
}
