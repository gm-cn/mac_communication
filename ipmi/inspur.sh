#!/bin/sh

log_file="/var/log/cdsstack/inspur_log"
date_info=`date`

function str_to_ascii()
{
	string=$1
	number=$2
	str_number="${#string}"
		
        if [[ $number -gt $str_number ]];then
		outnumber=$number
	else
		outnumber=$str_number
	fi

	for ((i=1;i<=$outnumber;i++))
	do
		str=`echo $string | cut -c $i`
		printf "0x%d " "'$str"
	done
}


function log_number()
{
	number=`cat $log_file |wc -l`
	log_numner=500
	if  [[ $number -gt  500 ]];then
		sed -i $log_file		
	fi
}

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
    ipmitool_commd="ipmitool -U $2 -P $3 -H $1 -I lanplus"
	$ipmitool_commd raw 0x04 0x12 0x09 0x02 0x28 0x12 0x00
	$ipmitool_commd raw 0x0c 0x01 0x01 0x12 0x02 0x06 0x03 0x03
	$ipmitool_commd raw 0x34 0x02 0x01 0x21 0x01 0x62 0x61 0x72 0x65 0x6d 0x65 0x74 0x61 0x6c 0x2e 0x61 0x6c 0x61 0x72 0x6d 0x40 0x63 0x61 0x70 0x69 0x74 0x61 0x6c 0x6f 0x6e 0x6c 0x69 0x6e 0x65 0x2e 0x6e 0x65 0x74
	$ipmitool_commd raw 0x04 0x12 0x06 0x01 0x80 0x01 0x01 0x00 0xff 0xff 0xff 0xff 0xff 0xff 0xff 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00
	$ipmitool_commd raw 0x0c 0x01 0x01 0x12 0x01 0x00 0x03 0x03
	$ipmitool_commd raw 0x04 0x16 0x01 0x02 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00
	if [[ $? != 0 ]]; then
		for((i=1;i<4;i++));
		do 
			sleep 5
			$ipmitool_commd raw 0x04 0x16 0x01 0x02 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00
			if [[ $? == 0 ]]; then
				echo "$date_info mail_alarm success" >> $log_file
				return 0
			fi
		done
		echo "$date_info mail_alarm failed" >> $log_fil
		return 1
	else
		echo "$date_info mail_alarm success" >> $log_file
		return 0
	fi
}

function function_cds_snmp_alarm()
{
        ipmitool_commd="ipmitool -U $2 -P $3 -H $1 -I lanplus"
	$ipmitool_commd raw 0x04 0x12 0x09 0x01 0x18 0x11 0x00
	$ipmitool_commd raw 0x0C 0x01 0x01 0x12 0x01 0x00 0x03 0x03
	$ipmitool_commd raw 0x0C 0x01 0x01 0x13 0x01 0x00 0x00 0x0A 0x80 0x65 0x36 0x00 0x00 0x00 0x00 0x00 0x00
	$ipmitool_commd raw 0x04 0x12 0x06 0x01 0x80 0x01 0x01 0x00 0xff 0xff 0xff 0xff 0xff 0xff 0xff 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00
	$ipmitool_commd raw 0x3c 0x19 0x00 0x02
	$ipmitool_commd raw 0x04 0x16 0x01 0x01 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00
	if [[ $? != 0 ]]; then
		echo "$date_info snmp alarm failed" >>$log_file
	else
		echo "$date_info snmp alarm success" >> $log_file
	fi

}

function function_cds_performance_config()
{
	ipmitool_commd="ipmitool -U $2 -P $3 -H $1 -I lanplus" 
	$ipmitool_commd raw 0x3c 0x48 0x01 0xfb 0x00 0x00
	$ipmitool_commd raw 0x3c 0x4a 0x02
	$ipmitool_commd raw 0x3c 0x49 0x01 0xfb | awk '{print $6}' | grep 00
	if [[ $? == 0 ]]; then
		echo "$date_info performance config success" >>$log_file
	else
		echo "$date_info performance config failed" >>$log_file
	fi
}

function function_cds_boot_set()
{
	ipmitool_commd="ipmitool -U $2 -P $3 -H $1 -I lanplus"
	$ipmitool_commd raw 0x00 0x08 0x05
	if [[ $4 == "Bios" ]]; then
		$ipmitool_commd raw 0x3c 0x48 0x00 0x2d 0x01 0x00
		$ipmitool_commd raw 0x3c 0x48 0x00 0x2e 0x02 0x00
		$ipmitool_commd raw 0x3c 0x48 0x00 0x2f 0x02 0x00
		$ipmitool_commd raw 0x3c 0x48 0x00 0x30 0x02 0x00
		$ipmitool_commd raw 0x3c 0x48 0x00 0x31 0x02 0x00
		
		$ipmitool_commd raw 0x3c 0x4a 0x02
        	if [[ $? != 0 ]]; then
        	        $ipmitool_commd raw 0x3c 0x49 0x00 0x2d | awk '{print $6}' | grep 01
	                if [[ $? != 0 ]]; then
                	        echo "$date_info boot set failed" >>$log_file
        	                return 1
	                else
				echo "$date_info boot set success" >>$log_file
                      	        return 0
                	fi
	        else
                	function_cds_power_off $1 $2 $3
        	        function_cds_power_on $1 $2 $3
	                echo "$date_info boot set success" >>$log_file
                	return 0
        	fi
	else
		$ipmitool_commd raw 0x3c 0x48 0x00 0x2d 0x02 0x00
		$ipmitool_commd raw 0x3c 0x48 0x00 0x2e 0x01 0x00
        $ipmitool_commd raw 0x3c 0x48 0x00 0x2f 0x01 0x00
        $ipmitool_commd raw 0x3c 0x48 0x00 0x30 0x01 0x00
        $ipmitool_commd raw 0x3c 0x48 0x00 0x31 0x01 0x00
		$ipmitool_commd raw 0x3c 0x4a 0x02
        if [[ $? != 0 ]]; then
            $ipmitool_commd raw 0x3c 0x49 0x00 0x2d | awk '{print $6}' | grep 02
            if [[ $? != 0 ]]; then
                echo "$date_info boot set failed" >>$log_file
                return 1
            else
                echo "$date_info boot set success" >>$log_file
                    return 0
            fi
        else
            function_cds_power_off $1 $2 $3
            function_cds_power_on $1 $2 $3
            echo "$date_info boot set success" >>$log_file
            return 0
        fi
	fi
}

function function_cds_numa_config()
{
	ipmitool_commd="ipmitool -U $2 -P $3 -H $1 -I lanplus"
	$ipmitool_commd raw 0x3c 0x48 0x00 0xd3 0x01 0x00
	$ipmitool_commd raw 0x3c 0x4a 0x02
	$ipmitool_commd raw 0x3c 0x49 0x00 0xd3 | awk '{print $6}' | grep 00
	if [[ $? == 0 ]]; then
		echo "$date_info numa config failed" >> $log_file
	else
		echo "$date_info numa config success" >> $log_file
	fi
}

function function_cds_pxe_config()
{
        ipmitool_commd="ipmitool -U $2 -P $3 -H $1 -I lanplus"
	str=$4
	if [[ $str == "" ]]; then
		str="1,2,3,4"
	fi
	for((a=0;a<${#str};a++));
	do
		i=${str:$a:1}
		if [[ $i == 1 ]]; then
			$ipmitool_commd raw 0x3c 0x48 0x00 0x32 0x01 0x00
		fi
	
		if [[ $i == 2 ]]; then
                        $ipmitool_commd raw 0x3c 0x48 0x00 0x33 0x01 0x00
                fi
		
		if [[ $i == 3 ]]; then
                        $ipmitool_commd raw 0x3c 0x48 0x00 0x34 0x01 0x00
                fi

		if [[ $i == 4 ]]; then
                        $ipmitool_commd raw 0x3c 0x48 0x00 0x35 0x01 0x00
                fi
	done
	$ipmitool_commd raw 0x3c 0x48 0x00 0x24 0x01 0x00	
	res=`$ipmitool_commd raw 0x3c 0x4a 0x02 | awk '{print $1}'`
	
	$ipmitool_commd raw 0x3c 0x49 0x00 0x24 | awk '{print $6}' | grep 01
	if [[ $? == 0 ]]; then
		echo "$date_info Ipv4 pxe support  success" >> $log_file
	else
		echo "$date_info Ipv4 pxe support  failed" >> $log_file
	fi
	
	$ipmitool_commd raw 0x3c 0x49 0x00 0x32 | awk '{print $6}' | grep 01
	if [[ $? != 0 ]]; then
		echo "$date_info pxe 1 config failed" >> $log_file
		return 1
	else
		echo "$date_info pxe 1 config success" >> $log_file
	fi
	
	$ipmitool_commd raw 0x3c 0x49 0x00 0x33 | awk '{print $6}' | grep 01
        if [[ $? != 0 ]]; then
                echo "$date_info pxe 2 config failed" >> $log_file
		return 1
        else
                echo "$date_info pxe 2 config success" >> $log_file
        fi
	
	$ipmitool_commd raw 0x3c 0x49 0x00 0x34 | awk '{print $6}' | grep 01
        if [[ $? != 0 ]]; then
                echo "$date_info pxe 3 config failed" >> $log_file
		return 1
        else
                echo "$date_info pxe 3 config success" >> $log_file
        fi

	$ipmitool_commd raw 0x3c 0x49 0x00 0x35 | awk '{print $6}' | grep 01
        if [[ $? != 0 ]]; then
                echo "$date_info pxe 4 config failed" >> $log_file
		return 1
        else
                echo "$date_info pxe 4 config success" >> $log_file
		return 0
        fi	
	

}

function function_cds_alarm_config()
{
        if [[ $? == 0 ]];then
	        echo "hostip:$1 $date_info alarm_config success" >> $log_file
        else
            echo "hostip:$1 $date_info alarm_config error" >> $log_file
        fi
}

function function_cds_boot_config()
{
        ipmitool_commd="ipmitool -U $2 -P $3 -H $1 -I lanplus"
	$ipmitool_commd raw 0x3c 0x48 0x02 0x13 0x03 0x00
	$ipmitool_commd raw 0x3c 0x4a 0x02
	$ipmitool_commd raw 0x3c 0x49 0x02 0x13 | awk '{print $6}' | grep 03
	if [[ $? == 0 ]]; then
		echo "$date_info host ip: $1 boot config success" >> $log_file
	else
		echo "$date_info host ip: $1 boot config failed" >> $log_file
	fi
}

function function_cds_get_sn()
{
    ipmitool_commd="ipmitool -U $2 -P $3 -H $1 -I lanplus"
	sn=`$ipmitool_commd fru | grep -w "Product Serial" | awk '{print $4}'`
	res=`$ipmitool_commd raw 0x3c 0x03 0x01 0x00`
	local bios=""
	for i in $res;
	do
		if [[ $i == 20 ]]; then
			break
		else
			dec=`echo $((16#$i))`
			str=`echo $dec | awk '{printf("%c", $1)}'`
			bios="$bios$str" 
		fi
	done
	str=`$ipmitool_commd raw 0x3c 0x37 0x00 | awk '{print $3}'`
	dec=`echo $((16#$str))`
	bmc="$dec"
	str=`$ipmitool_commd raw 0x3c 0x37 0x00 | awk '{print $4}'`
        dec=`echo $((16#$str))`
        bmc="$bmc.$dec"
	str=`$ipmitool_commd raw 0x3c 0x37 0x00 | awk '{print $5}'`
        dec=`echo $((16#$str))`
        bmc="$bmc.$dec"
	string="$bios,$bmc,$sn"
	echo $string
}

function function_cds_get_mac()
{
	ipmitool_commd="ipmitool -U $2 -P $3 -H $1 -I lanplus"
    mac=`$ipmitool_commd lan print | grep -w "MAC Address" | awk '{print $4}'`
	echo "mac address is $mac"
	return 0
}

function function_cds_config_raid()
{
        if [[ $? == 0 ]];then
	        echo "hostip:$1 $date_info alarm_config success" >> $log_file
        else
                echo "hostip:$1 $date_info alarm_config error" >> $log_file
        fi
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
    echo "inspur does not support change timezone"
    return 0
}

function function_cds_bios_update()
{
	echo "inspur does not currently support bios update"
}


function function_cds_idrac_update()
{
	echo "inspur does not currently support idrac update"
}

function function_cds_single_sn()
{
    ipmitool_commd="ipmitool -U $2 -P $3 -H $1 -I lanplus"
	sn=`$ipmitool_commd fru | grep -w "Product Serial" | awk '{print $4}'`
	echo $sn
}

function function_cds_vnc_control()
{
	echo "inspur does not support vnc"
}
