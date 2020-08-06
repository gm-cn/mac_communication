#!/bin/sh
log_file="/var/log/cdsstack/dell_log"
date_info=`date`
cmd_dir="/opt/dell/srvadmin/sbin/racadm"
update_file_path="/tftpboot/update_file/"
function_cds_add_bmc_user()
{
	racadm_comm="$cmd_dir -r $1 -u $2 -p $3 --nocertwarn"
	flag=0
	m=3
	for((i=3;i<17;i++));
	do
		$racadm_comm get iDRAC.Users.$i.UserName | grep $4
		if [[ $? == 0 ]]; then
			$racadm_comm set iDRAC.Users.$i.Password "$5"
			echo "hostip:$1 $date_info change password username:$4  password:$5 success" >> $log_file
			flag=1
			return 0
		fi
		
		$racadm_comm get iDRAC.Users.$i.Enable | grep Disabled
		if [[ $? == 0 ]]; then
			break
		fi
	done
	
	if [[ $flag == 0 ]]; then			
		for((j=3;j<17;j++));
		do
			$racadm_comm get iDRAC.Users.$j.Enable | grep Disabled
			if [[ $? == 0 ]]; then
				m=$j
				break
			fi
		done
	fi

    $racadm_comm set iDRAC.Users.$m.UserName "$4"
	$racadm_comm set iDRAC.Users.$m.Password "$5"
	$racadm_comm set iDRAC.Users.$m.IpmiLanPrivilege 4
	$racadm_comm set iDRAC.Users.$m.IpmiSerialPrivilege 4
	$racadm_comm set iDRAC.Users.$m.ProtocolEnable 1
	$racadm_comm set iDRAC.Users.$m.Privilege 1
	$racadm_comm set iDRAC.Users.$m.SolEnable 1
	$racadm_comm set iDRAC.Users.$m.Enable 1
	$racadm_comm set iDRAC.Users.$m.Privilege 511
	$racadm_comm get iDRAC.Users.$m.UserName | grep $4 
	if [[ $? == 0 ]]; then
        echo "hostip:$1 $date_info add bmc username:$4  password:$5 success" >> $log_file
        return 0
    else
        echo "hostip:$1 $data_info add bmc username:$4  password:$5 error" >> $log_file
        return 1
    fi
}

function function_cds_delete_bmc_user()
{
	racadm_comm="$cmd_dir -r $1 -u $2 -p $3 --nocertwarn"
	for((i=3;i<17;i++));
	do 
		$racadm_comm get iDRAC.Users.$i.UserName | grep $4
		if [[ $? == 0 ]]; then
			$racadm_comm set iDRAC.Users.$i.IpmiLanPrivilege 15
			$racadm_comm set iDRAC.Users.$i.IpmiSerialPrivilege 15
			$racadm_comm set iDRAC.Users.$i.ProtocolEnable 0
			$racadm_comm set iDRAC.Users.$i.Privilege ""
			$racadm_comm set iDRAC.Users.$i.SolEnable 0
			$racadm_comm set iDRAC.Users.$i.Enable 0
			$racadm_comm set iDRAC.Users.$i.UserName ""
			
			echo "hostip:$1 $date_info delete username:$4  success" >> $log_file
			echo "$i"
			return 0
		fi
	done
	echo "hostip:$1 $date_info delete username:$4 error user name does not exist" >> $log_file
	return 1
}

function function_cds_vnc_config()
{
	racadm_comm="$cmd_dir -r $1 -u $2 -p $3 --nocertwarn"
    $racadm_comm  set iDRAC.VNCServer.Enable 1
    $racadm_comm  set iDRAC.VNCServer.Password "$4"
	$racadm_comm  get iDRAC.VNCServer.Enable | grep Enabled
	if [[ $? == 0 ]]; then
        echo "hostip:$1 $date_info vnc config  success" >> $log_file
        return 0
    else
        echo "hostip:$1 $data_info vnc config error" >> $log_file
        return 1
    fi
        
        
}

function function_cds_mail_alarm()
{
	racadm_comm="$cmd_dir -r $1 -u $2 -p $3 --nocertwarn"
    $racadm_comm set iDRAC.IPMILan.AlertEnable Enabled
	$racadm_comm set iDRAC.IPMILan.Enable 1
	$racadm_comm set iDRAC.EmailAlert.1.Enable 1
	$racadm_comm set iDRAC.EmailAlert.1.Address baremetal.alarm@capitalonline.net
	$racadm_comm set idrac.remotehosts.SMTPServerIPAddress 117.79.130.234
	$racadm_comm get iDRAC.EmailAlert.1.Enable | grep Enabled
	sleep 1 
	if [[ $? == 0 ]]; then
        echo "hostip:$1 $date_info mail:baremetal.alarm@capitalonline.net alarm  success" >> $log_file
        return 0
    else
        echo "hostip:$1 $data_info mail:baremetal.alarm@capitalonline.net alarm error" >> $log_file
        return 1
    fi
	
}

function function_cds_snmp_alarm()
{
	racadm_comm="$cmd_dir -r $1 -u $2 -p $3 --nocertwarn"
    $racadm_comm set iDRAC.IPMILan.AlertEnable enabled
	$racadm_comm set iDRAC.SNMP.TrapFormat SNMPv2
	$racadm_comm set iDRAC.SNMP.Alert.1.DestAddr 10.128.101.54
	$racadm_comm set iDRAC.SNMP.Alert.1.Enable 1
    $racadm_comm get iDRAC.SNMP.Alert.1.DestAddr | grep "10.128.101.54"
 	
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
	racadm_comm="$cmd_dir -r $1 -u $2 -p $3 --nocertwarn"
    $racadm_comm set System.ThermalSettings.ThermalProfile 1
    $racadm_comm set bios.sysprofilesettings.sysprofile PerfOptimized

        sysprofile=`$racadm_comm get  bios.sysprofilesettings.sysprofile | grep PerfOptimized | wc -l`
	if [[ $sysprofile == 1 ]];then
        echo "hostip:$1 $date_info performance_config PerfOptimized success" >> $log_file
        return 0
    else
        echo "hostip:$1 $date_info performance_config PerfOptimized error" >> $log_file
        return 1
    fi
}

function check()
{
	jobID=$4
	racadm_comm="$cmd_dir -r $1 -u $2 -p $3 --nocertwarn"
	start=`date`
	let limit=0
	while [ 1 ] 
	do
		sleep 20
		let limit++
		$racadm_comm jobqueue view -i $jobID | grep -w Percent | tr -d "Percent Complete=[]" | grep -w 100
		if [[ $? == 0 ]]; then
			end=`date`
			echo "Job start at: $start end at : $end  success" >> $log_file
			return 0
			break
		fi
		if [[ $limit -ge 30 ]]; then
			echo "Job timeout  error" >> $log_file
			return 1
			break
		fi
	done

}

function boot_bios()
{
	racadm_comm="$cmd_dir -r $1 -u $2 -p $3 --nocertwarn"
	$racadm_comm set BIOS.BiosBootSettings.BootMode $4
	if [[ $? == 215 ]]; then
        function_cds_error_message boot_set 215
    fi
	jobID=`$racadm_comm jobqueue create BIOS.Setup.1-1 -s TIME_NOW -r Forced | grep -w "Commit JID =" | tr -d "\n\r" | awk '{print $4}' `
        if [[ $jobID != "" ]];	then
		#function_cds_power_off $1 $2 $3
        	#function_cds_power_on $1 $2 $3
	        check $1 $2 $3 $jobID
	fi
	$racadm_comm get BIOS.BiosBootSettings.BootMode | grep $4
	return $?


}

function function_cds_boot_set()
{
	type=$4
	boot_bios $1 $2 $3 $type
	if [[ $? == 0 ]];then
	        echo "hostip:$1 $date_info set boot type: $type success" >> $log_file
	        return 0
        else
                echo "hostip:$1 $date_info set boot type: $type error" >> $log_file
                return 1
        fi
}

function function_cds_numa_config()
{
	racadm_comm="$cmd_dir -r $1 -u $2 -p $3 --nocertwarn"
	$racadm_comm set bios.memsettings.nodeinterleave Enabled
     	nodeinterleave=`$racadm_comm get  bios.memsettings.nodeinterleave | grep Enabled | wc -l`

	if [[ $nodeinterleave == 1 ]];then
        echo "hostip:$1 $date_info close numa   success" >> $log_file
            return 0
        else
            echo "hostip:$1 $date_info close numa  Bios error" >> $log_file
            return 1
        fi
}

function function_cds_pxe_config()
{
	racadm_comm="$cmd_dir -r $1 -u $2 -p $3 --nocertwarn"
	bios_mode=`$racadm_comm get BIOS.BiosBootSettings.BootMode | sed -n '2p' | tr -s "=" " " | tr -d "\r" | awk '{print $2}'`
	if [[ $bios_mode == "Uefi" ]]; then
		local str=$4
		if [[ $str == "" ]]; then
		    str="1"
			local nic_count=`$racadm_comm get nic.nicconfig | tr -s '\n' | wc -l`
			let order=2
			while [ $order -le $nic_count ]
			do
			    str="${str},${order}"
			    let order++
			done
		fi
		let device_number=1
		for((a=0;a<${#str};a++));
		do
            local i=${str:$a:1}
            if [[ $i != "," ]]; then
        	    local NIC_info=`$racadm_comm get NIC.nicconfig.$i | sed -n '1,1'p | tr -s "=#" : | cut -d ":" -f 2`
				local NIC_info1=`$racadm_comm hwinventory NIC | grep "$NIC_info" | cut -d  ":" -f 1 | sed -n "2p"`
				$racadm_comm hwinventory $NIC_info | grep "Link Speed" | grep "Not Applicable"
				local nic_result=$?
				$racadm_comm hwinventory $NIC_info1 | grep "Link Speed" | grep "Not Applicable"
                local nic1_result=$?

				if [[ $NIC_info1 == "" ]]; then
					nic1_result=0
				fi
				if [[ $nic_result == 0 && $nic1_result == 0 ]]; then
                    echo "NIC $NIC_info is not avaiable" >> $log_file
                else
                    $racadm_comm  set  BIOS.NetworkSettings.PxeDev${device_number}EnDis Enabled
                    if [[ $? == 215 ]]; then
						function_cds_error_message pxe_config 215
					fi
                    $racadm_comm  set  BIOS.PxeDev${device_number}Settings.PxeDev${device_number}Interface $NIC_info
                    $racadm_comm  get  nic.nicconfig.${device_number} | grep WakeOnLan
                    if [[ $? == 0 ]]; then
                        $racadm_comm  set  nic.nicconfig.${device_number}.WakeOnLan Disabled
                        local WakeOnLan=`$racadm_comm get  nic.nicconfig.${device_number}.WakeOnLan | grep Disabled | wc -l`
                     else
                        local WakeOnLan=1
                     fi
					$racadm_comm get nic.nicconfig.${device_number} | grep LegacyBootProto
					if [[ $? == 0 ]]; then
						$racadm_comm  set  nic.nicconfig.${device_number}.LegacyBootProto PXE
                        local LegacyBootProto=`$racadm_comm  get  nic.nicconfig.${device_number}.LegacyBootProto | grep PXE | wc -l`
					else
						LegacyBootProto=1
					fi

                    local PxeDevInterface=`$racadm_comm get  BIOS.PxeDev${device_number}Settings.PxeDev${device_number}Interface | grep $NIC_info | wc -l`

                    local PxeDevEnDis=`$racadm_comm get BIOS.NetworkSettings.PxeDev${device_number}EnDis | grep Enabled | wc -l`

                    if [[ $PxeDevInterface == 1  && $LegacyBootProto == 1 && $WakeOnLan == 1 && $PxeDevEnDis == 1 ]];then
                        echo "hostip:$1 $date_info device $device_number NIC  $NIC_info pxe config   success" >> $log_file
                    else
                        echo "hostip:$1 $date_info device $device_number NIC  $NIC_info pxe config error" >> $log_file
                        return 1
                    fi
					let device_number++
				fi
			fi
		done
		local jobID=`$racadm_comm jobqueue create BIOS.Setup.1-1 -s TIME_NOW -r Forced | grep -w "Commit JID =" | tr -d "\n\r" | awk '{print $4}'`
                if [[ $jobID != "" ]]; then
			        #function_cds_power_off $1 $2 $3
                    #function_cds_power_on $1 $2 $3
                    check $1 $2 $3 $jobID
                    return $?
                fi
                return 0
	else
		local boot_seq=""
		local str=$4
                if [[ $str == "" ]]; then
                    str="1"
                    local nic_count=`$racadm_comm get nic.nicconfig | tr -s '\n' | wc -l`
                    let order=2
                    while [ $order -le $nic_count ]
                    do
                        str="${str},${order}"
                        let order++
                    done
                fi
                let device_number=1
                for((a=0;a<${#str};a++));
                do
                        local i=${str:$a:1}
                        if [[ $i != "," ]]; then
                                local NIC_info=`$racadm_comm get NIC.nicconfig.$i | sed -n '1,1'p | tr -s "=#" : | cut -d ":" -f 2`
                                $racadm_comm hwinventory $NIC_info | grep "Link Speed" | grep "Not Applicable"
                                if [[ $? == 0 ]]; then
                                        echo "NIC $NIC_info is not avaiable" >> $log_file
                                else
					                #$racadm_comm get bios.biosbootsettings.bootseq | grep $NIC_info
                                    #if [[ $? == 0 ]]; then
                                    $racadm_comm set NIC.nicconfig.$i.Legacybootproto PXE
                                    if [[ $boot_seq == "" ]]; then
                                        boot_seq="$NIC_info"
                                    else
                                        boot_seq="$boot_seq,$NIC_info"
                                    fi
                                fi
                        fi
                done
		$racadm_comm set BIOS.BiosBootSettings.BootSeq $boot_seq
		local jobID=`$racadm_comm jobqueue create BIOS.Setup.1-1 -s TIME_NOW -r Forced| grep -w "Commit JID =" | tr -d "\n\r" | awk '{print $4}'`
	        if [[ $jobID != "" ]]; then
        	        #function_cds_power_off $1 $2 $3
                	#function_cds_power_on $1 $2 $3
	                check $1 $2 $3 $jobID
        	fi

                $racadm_comm get BIOS.BiosBootSettings.BootSeq | grep "$boot_seq"

        	if [[ $? == 0 ]]; then
                	echo "PXE setting success" >> $log_file
	                return 0
        	else
                	echo "PXE setting error" >> $log_file
			return 1
		fi
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

function bios_bootseq()
{
        racadm_comm="$cmd_dir -r $1 -u $2 -p $3 --nocertwarn"

        local boot_seq_info=""
        nic_count=`$racadm_comm get NIC.nicconfig | tr -i '\n' |wc -l`
        let a=1
        while [ $a -le $nic_count ]
        do
            let a++
            NIC_info=`$racadm_comm get NIC.nicconfig.$a | sed -n '1,1'p | tr -s "=#" : | cut -d ":" -f 2`
            $racadm_comm get BIOS.BiosBootSettings.BootSeq | grep $NIC_info
            ret=`echo $?`
            if [[ $ret == 0 ]]; then
                $racadm_comm hwinventory $NIC_info | grep "Link Speed" | grep "Not Applicable"
                if [[ $? == 1 ]]; then
                    if [[ $boot_seq_info == "" ]]; then
                        boot_seq_info="$NIC_info"
                    else
                        boot_seq_info="$boot_seq_info,$NIC_info"
				    fi
			    fi
			fi
	    done
        $racadm_comm set BIOS.BiosBootSettings.BootSeq $boot_seq_info
        if [[ $jobID != "" ]]; then
		jobID=`$racadm_comm jobqueue create BIOS.Setup.1-1 -s TIME_NOW -r Forced | grep -w "Commit JID =" | tr -d "\n\r" | awk '{print $4}' `
	        #function_cds_power_off $1 $2 $3
        	#function_cds_power_on $1 $2 $3
	        check $1 $2 $3 $jobID
	fi
	$racadm_comm get BIOS.BiosBootSettings.BootSeq | grep "$boot_seq_info"
	if [[ $? == 0 ]];then
	        echo "hostip:$1 $date_info BootSeq $boot_seq_info success" >> $log_file
	        return 0
        else
                echo "hostip:$1 $date_info BootSeq $boot_seq_info error" >> $log_file
                return 1
        fi

}

function uefi_bootseq()
{
        racadm_comm="$cmd_dir -r $1 -u $2 -p $3 --nocertwarn"
	local boot_seq_info=""
	$racadm_comm get BIOS.BiosBootSettings.UefiBootSeq | grep -w NIC.PxeDevice.1-1
	if [[ $? == 0 ]]; then
		boot_seq_info="NIC.PxeDevice.1-1"
	fi

	$racadm_comm get BIOS.BiosBootSettings.UefiBootSeq | grep -w NIC.PxeDevice.2-1
        if [[ $? == 0 ]]; then
                if [[ $boot_seq_info == "" ]]; then
			boot_seq_info="NIC.PxeDevice.2-1"
		else
			boot_seq_info="$boot_seq_info,NIC.PxeDevice.2-1"
        	fi
	fi

	$racadm_comm get BIOS.BiosBootSettings.UefiBootSeq | grep -w NIC.PxeDevice.3-1
        if [[ $? == 0 ]]; then
                if [[ $boot_seq_info == "" ]]; then
			boot_seq_info="NIC.PxeDevice.3-1"
		else
			boot_seq_info="$boot_seq_info,NIC.PxeDevice.3-1"
        	fi
	fi

	$racadm_comm get BIOS.BiosBootSettings.UefiBootSeq | grep -w NIC.PxeDevice.4-1
        if [[ $? == 0 ]]; then
                if [[ $boot_seq_info == "" ]]; then
			boot_seq_info="NIC.PxeDevice.4-1"
		else
			boot_seq_info="$boot_seq_info,NIC.PxeDevice.4-1"
        	fi
	fi


    $racadm_comm set BIOS.BiosBootSettings.UefiBootSeq $boot_seq_info
	if [[ $? == 201 ]]; then
		function_cds_error_message boot_seq 201
	fi

	jobID=`$racadm_comm jobqueue create BIOS.Setup.1-1 -s TIME_NOW -r Forced | grep -w "Commit JID =" | tr -d "\n\r" | awk '{print $4}'`
	if [[ $jobID != "" ]]; then
		#function_cds_power_off $1 $2 $3
        	#function_cds_power_on $1 $2 $3
        	check $1 $2 $3 $jobID
	fi
	$racadm_comm get BIOS.BiosBootSettings.UefiBootSeq | grep "$boot_seq_info"
	if [[ $? == 0 ]]; then
	        echo "hostip:$1 $date_info BootSeq $boot_seq_info success" >> $log_file
	        return 0
        else
                echo "hostip:$1 $date_info BootSeq $boot_seq_info error" >> $log_file
                return 1
        fi
}

function function_cds_boot_config_set()
{
	racadm_comm="$cmd_dir -r $1 -u $2 -p $3 --nocertwarn"
	type_boot=`$racadm_comm get BIOS.BiosBootSettings.BootMode |grep BootMode | awk '{print $1}'|cut -d '=' -f 2 |tr -d '\\r' `

	if [[ "$type_boot" == "Bios" ]];then
	        bios_bootseq $1 $2 $3
	else
	        uefi_bootseq $1 $2 $3
	fi
	return $?
}

function function_cds_boot_config_get()
{
	racadm_comm="$cmd_dir -r $1 -u $2 -p $3 --nocertwarn"
	type_boot=`$racadm_comm get BIOS.BiosBootSettings.BootMode |grep BootMode | cut -d '=' -f 2 |tr -d '\\r' `
	if [[ "$type_boot" == "Bios" ]];then
	        $racadm_comm get BIOS.BiosBootSettings.Bootseq
	else
	        $racadm_comm get BIOS.BiosBootSettings.UefiBootseq
	fi
	return 0
}

function function_cds_boot_config()
{
        flag_type="$4"
	if [[ "$flag_type" == "set" || "$flag_type" == "" ]];then
	        function_cds_boot_config_set $1 $2 $3
	else
	        function_cds_boot_config_get $1 $2 $3
	fi
	return $?
}

function function_cds_get_sn()
{
    racadm_comm="$cmd_dir -r $1 -u $2 -p $3 --nocertwarn"
	sleep 3
	for ((i=0;i<30;i++))
	do 
		local Firmware_Version=`$racadm_comm getsysinfo | grep "Firmware Version" | awk '{print $4}' | tr "\n" "\t" | sed s/[[:space:]]//g`
		if [[ $Firmware_Version != "" ]]; then
			break
		fi
		sleep 5
	done
	if [[ $$Firmware_Version == "" ]]; then
		return 1
	fi
	sleep 5
	Service_Tag=`$racadm_comm getsysinfo | grep "Service Tag" | awk '{print $4}' | tr -s "\n" "\t"`
	BIOS_Version=`$racadm_comm getsysinfo | grep "System BIOS Version" | awk '{print $5}' | tr "\n" "\t"`
	#power_reden=`$racadm_comm get system.power.redundancypolicy | head -1 | tr -d "\\r"`
	string="$BIOS_Version,$Firmware_Version,$Service_Tag"
	echo $string
}

function function_cds_single_sn()
{
    racadm_comm="$cmd_dir -r $1 -u $2 -p $3 --nocertwarn"
    Service_Tag=`$racadm_comm getsysinfo | grep "Service Tag" | awk '{print $4}' | tr "\n" "\t"`
	echo $Service_Tag
}

function function_cds_get_mac()
{
	racadm_comm="$cmd_dir -r $1 -u $2 -p $3 --nocertwarn"
	Service_Tag=`$racadm_comm getsysinfo | grep "Service Tag" | awk '{print $4}' | tr "\n" "\t"`
	MAC_address=`$racadm_comm getsysinfo | grep Ethernet | sort | awk '{print $4}' | tr "\n" "\t"`
	result1="$ipmi_ip \t $Service_Tag \t $MAC_address"
	echo -e $result1 >>mac_list.txt
}

function function_cds_config_raid()
{
	racadm_comm="$cmd_dir -r $1 -u $2 -p $3 --nocertwarn"

	controller=`$racadm_comm storage get controllers | grep RAID | tr -d "\r" | sed s/[[:space:]]//g`
	str=$5
	local raid="$racadm_comm storage createvd:$controller -rl r$4 -pdkey:"

	for((a=0;a<${#str};a++));
	do
		i=${str:$a:1}
		if [[ $i != "." && $i != "," ]]; then

			pdisk=`$racadm_comm storage get pdisks | grep -w "Disk.Bay.$i" | tr -d "\r" | sed s/[[:space:]]//g`
			if [[ $4 == 0 ]]; then
				raid=`echo ${raid}$pdisk,\\`
        		fi

	       		if [[ $4 == 1 ]]; then
        			raid=`echo ${raid}$pdisk,\\`
			fi

		        if [[ $4 == 5 ]]; then
				raid=`echo ${raid}$pdisk,\\`
	        	fi

	       		if [[ $4 == 10 ]]; then
				raid=`echo ${raid}$pdisk,\\`
	        	fi

		fi

		if [[ $i == "," ]]; then
			if [[ $4 == 0 ]]; then
                            $raid
                        fi

                        if [[ $4 == 1 ]]; then
                            $raid
                        fi

                        if [[ $4 == 5 ]]; then
                            $raid
                        fi

                        if [[ $4 == 10 ]]; then
                            $raid
                        fi

			$racadm_comm jobqueue create $controllers -r Forced
		        if [[ $? == 0 ]]; then
                    echo "hostip:$1 $date_info raid created success" >>$log_file

        		else
                    echo "hostip:$1 $date_info raid created error" >>$log_file
                    return 1
        		fi


		fi
	done

	if [[ $4 == 0 ]]; then
		$raid
        fi

        if [[ $4 == 1 ]]; then
                $raid
        fi

        if [[ $4 == 5 ]]; then
                $raid
        fi

        if [[ $4 == 10 ]]; then
                $raid
        fi
	$racadm_comm jobqueue create $controller -r Forced
	if [[ $? == 0 ]]; then
		echo "hostip:$1 $date_info raid created success" >>$log_file
		return 0
	else
		echo "hostip:$1 $date_info raid created error" >>$log_file
		return 1
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
	fi
        echo "hostip:$1 $date_info power reset   success" >> $log_file
}

function function_cds_submit_onetime()
{
	racadm_comm="$cmd_dir -r $1 -u $2 -p $3 --nocertwarn"
	function_cds_pxe_config $1 $2 $3 $pxe_device
	function_cds_boot_config $1 $2 $3 $flag_type
	function_cds_performance_config $1 $2 $3
	function_cds_numa_config $1 $2 $3
	jobID=`$racadm_comm jobqueue create BIOS.Setup.1-1 -s TIME_NOW | grep -w "Commit JID =" | tr -d "\n\r" | awk '{print $4}'`
	if [[ $jobID == "" ]]; then
		echo "job cannot create error"
		return 1
	fi
	function_cds_power_off $1 $2 $3
	function_cds_power_on $1 $2 $3
	check $1 $2 $3 $jobID
	return $?
}

function function_cds_vnc_control()
{
    start=`date`
	racadm_comm="$cmd_dir -r $1 -u $2 -p $3 --nocertwarn"
    vncSession=`$racadm_comm get idrac.vncserver.activesessions | grep ActiveSessions | tr '=' ' ' | awk '{print $2}'| tr -d '\r'`
    if [[ $vncSession != 0 ]]; then
        $racadm_comm set idrac.vncserver.enable 0
        $racadm_comm set idrac.vncserver.enable 1
		sleep 3
		end=`date`
        start_seconds=$(date --date="$start" +%s)
        end_seconds=$(date --date="$end" +%s)
        echo "hostip:$1 $date_info vnc conflict fixed success ,run in "$((end_seconds-start_seconds))"s"
		return 0
    fi

    $racadm_comm getssninfo | grep "Virtual Console"
    if [[ $? == 0 ]]; then
		$racadm_comm closessn -a
	fi
	end=`date`
    start_seconds=$(date --date="$start" +%s)
    end_seconds=$(date --date="$end" +%s)
    echo "hostip:$1 $date_info vnc conflict fixed success ,run in "$((end_seconds-start_seconds))"s"
}

function function_cds_vnc_control_new()
{
	start=`date`
	racadm_comm="$cmd_dir -r $1 -u $2 -p $3 --nocertwarn"
	#$racadm_comm set idrac.vncserver.enable 0
    #$racadm_comm set idrac.vncserver.enable 1
    $racadm_comm closessn -a
	end=`date`
    start_seconds=$(date --date="$start" +%s)
    end_seconds=$(date --date="$end" +%s)
    echo "hostip:$1 $date_info vnc conflict fixed success ,run in "$((end_seconds-start_seconds))"s"
}

function function_cds_change_timezone()
{
    racadm_comm="$cmd_dir -r $1 -u $2 -p $3 --nocertwarn"
    $racadm_comm get idrac.time | grep Shanghai
    if [[ $? == 0 ]]; then
        echo "Time zone already China"
    else
        echo "changing time zone to Asia/Shanghai"
        $racadm_comm set idrac.time.timezone Asia/Shanghai
        $racadm_comm set idrac.time.timezoneoffset 480
        echo "changing success now is $date_info"
    fi
}

function function_cds_bios_update()
{
	racadm_comm="$cmd_dir -r $1 -u $2 -p $3 --nocertwarn"
	if [[ $6 != "" ]]; then
		file_path="$6"
	else
		file_path="$update_file_path"
	fi
	if [[ $5 == True ]]; then
	    $racadm_comm jobqueue delete --all
		result=`$racadm_comm update -f $file_path$4 --reboot`
        result_code=$?
		if [[ $result_code != 0 && $result_code == 217 ]]; then
			function_cds_error_message bios_update 217
		fi
		if [[ $result_code != 0 ]]; then
			echo $result | grep "The file used for the operation is invalid"
			if [[ $? == 0 ]]; then
				function_cds_error_message bios_update 3 
			fi
			echo $result | grep "The syntax of the specified command is not correct."	
			if [[ $? == 0 ]]; then
				function_cds_error_message bios_update 2
			fi
			echo "hostip:$1 $date_info bios update error" >> $log_file
			function_cds_error_message bios_update 4
		fi
		
		jobID=`$racadm_comm jobqueue view | tail -n 20 | grep JID | tr "=]" " " | awk '{print $3}'`
		check $1 $2 $3 $jobID
		if [[ $? == 0 ]]; then
		    echo "hostip:$1 $date_info bios update success" >> $log_file
      		return 0
    	else
      		echo "hostip:$1 $date_info bios update error" >> $log_file
      		return 1
    	fi
	else
	    $racadm_comm jobqueue delete --all
		result=`$racadm_comm update -f $file_path$4`
		result_code=$?
		if [[ $result_code != 0 && $result_code == 217 ]]; then
        	function_cds_error_message bios_update 217
		fi
        if [[ $result_code != 0 ]]; then
            echo $result | grep "The file used for the operation is invalid"
            if [[ $? == 0 ]]; then
            	function_cds_error_message bios_update 3
			fi
            echo $result | grep "The syntax of the specified command is not correct."
            if [[ $? == 0 ]]; then
            	function_cds_error_message bios_update 2
			fi
            echo "hostip:$1 $date_info bios update error" >> $log_file
            function_cds_error_message bios_update 4
        fi
		echo "hostip:$1 $date_info bios update success and will take effect on next boot" >> $log_file
		return 0
	fi

}


function function_cds_idrac_update()
{
	racadm_comm="$cmd_dir -r $1 -u $2 -p $3 --nocertwarn"
	$racadm_comm jobqueue delete --all
	result=`$racadm_comm update -f $update_file_path$4`
	result_code=$?
        if [[ $result_code != 0 && $result_code == 217 ]]; then
        	function_cds_error_message idrac_update 217
		fi
        if [[ $result_code != 0 ]]; then
            echo $result | grep "The file used for the operation is invalid"
            if [[ $? == 0 ]]; then
            	function_cds_error_message idrac_update 3
			fi
            echo $result | grep "The syntax of the specified command is not correct."
            if [[ $? == 0 ]]; then
            	function_cds_error_message idrac_update 2
			fi
            echo "hostip:$1 $date_info idrac update error" >> $log_file
			function_cds_error_message idrac_update 4
		fi
	sleep 20
	jobID=`$racadm_comm jobqueue view | tail | grep JID | tr "=]" " " | awk '{print $3}'`
	check $1 $2 $3 $jobID
	if [[ $? != 0 ]]; then
		echo "hostip:$1 $date_info idrac update error" >> $log_file
	fi
	ping_test $1
	if [[ $? == 0 ]]; then
		echo "hostip:$1 $date_info idrac update success" >> $log_file
	else
		echo "hostip:$1 $date_info idrac update error" >> $log_file
	fi
}

function function_cds_single_sn()
{
    racadm_comm="$cmd_dir -r $1 -u $2 -p $3 --nocertwarn"
	Service_Tag=`$racadm_comm getsysinfo | grep "Service Tag" | awk '{print $4}' | tr "\n" "\t"`
	echo $Service_Tag
}

function ping_test()
{
	let limit=0
	while [ 1 ]
	do
		sleep 60
		let limit++
		ping $1 -c1
		if [[ $? == 0 ]]; then
			return 0
			break
		fi
		if [[ $limit -ge 20 ]]; then
			return 1
			break
		fi
	done
}

function function_cds_error_message()
{
	echo $1
	case $1 in
		pxe_config)
			case $2 in
				215)
					exit 5
					;;
				*)
					exit 4
					;;
			esac
			;;
		boot_set)
			case $2 in
                215)
                    exit 5
                    ;;
                *)
                    exit 4
                    ;;
            esac
            ;;
		bios_update)
			case $2 in
                217)
                    exit 217
                    ;;
                2)
					exit 2
					;;
				3)
					exit 3
					;;
				4)
					exit 4
					;;
				*)
                    exit 4
                    ;;
            esac
            ;;
		idrac_update)
			case $2 in
            	217)
                    exit 217
                    ;;
                2)
                    exit 2
                    ;;
                3)
                    exit 3
                    ;;
                4)
                    exit 4
                    ;;
                *)
                    exit 4
                    ;;
			esac
            ;;
		boot_seq)
			case $2 in
                201)
                    exit 5
                    ;;
                *)
                    exit 4
                    ;;
            esac
            ;;
	esac	
	
}
