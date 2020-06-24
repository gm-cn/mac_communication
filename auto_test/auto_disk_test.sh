#!/bin/bash

# This script is to ###
dev="/dev/sda"
function find_system()
{
	disk=`df -l |grep "boot" |awk '{print $1}' |cut -d '/' -f 3`
	sdx_nu=`echo  ${disk:0:3}`
        echo  $sdx_nu
}

function fio_seqread()
{
	fio -filename=$1 -direct=1 -iodepth 128 -thread -rw=read  -ioengine=libaio -bs=128k -size=1G -numjobs=1 -runtime=$2 -group_reporting -name=read |grep "IOPS"|cut -d "=" -f 3 |awk '{print $1}'
}

function fio_seqwrite()
{
	fio -filename=$1 -direct=1 -iodepth 128 -thread -rw=write  -ioengine=libaio -bs=128k -size=1G -numjobs=1 -runtime=$2 -group_reporting -name=read |grep "IOPS"|cut -d "=" -f 3 |awk '{print $1}'
}

function fio_randwrite()
{
	fio -filename=$1 -direct=1 -iodepth 32 -thread -rw=randread  -ioengine=libaio -bs=4k -size=1G -numjobs=4 -runtime=$2 -group_reporting -name=randread |grep "IOPS"|cut -d "=" -f 2 |awk '{print $1}'
}

function fio_randread()
{
	fio -filename=$1 -direct=1 -iodepth 1 -thread -rw=randwrite  -ioengine=libaio -bs=4k -size=1G -numjobs=4 -runtime=$2  -group_reporting -name=randwrite|grep "IOPS"|cut -d "=" -f 2 |awk '{print $1}'
}

function fio_read_lat()
{
	fio -filename=$1 -direct=1 -iodepth 1 -thread -rw=read  -ioengine=libaio -bs=128k -size=1G -numjobs=1 -runtime=$2 -group_reporting -name=read |grep -w  lat |grep avg |awk '{print $5}'|cut -d '=' -f 2	
}

function fio_write_lat()
{
	fio -filename=$1 -direct=1 -iodepth 1 -thread -rw=write  -ioengine=libaio -bs=128k -size=1G -numjobs=1 -runtime=$2 -group_reporting -name=write |grep -w  lat |grep avg |awk '{print $5}'|cut -d '=' -f 2
}

function fio_randread_lat()
{
       fio -filename=$1 -direct=1 -iodepth 1 -thread -rw=randread  -ioengine=libaio -bs=128k -size=1G -numjobs=1 -runtime=$2 -group_reporting -name=randread |grep -w  lat |grep avg |awk '{print $5}'|cut -d '=' -f 2
}

function fio_randwrite_lat()
{
	fio -filename=$1 -direct=1 -iodepth 1 -thread -rw=randwrite  -ioengine=libaio -bs=128k -size=1G -numjobs=1 -runtime=$2 -group_reporting -name=randwrite |grep -w  lat |grep avg |awk '{print $5}'|cut -d '=' -f 2
}

function sysytem_disk()
{
        Devlist=`find_system`
        status="success"
        SN=`smartctl -i /dev/$Devlist |grep Serial |awk '{print $3}'`
        health=`smartctl -H /dev/$Devlist |grep Health |awk '{print $4}'`

        if [[ "$RSC" == "" ]];then
                RSC=0
        fi
        if [[  "$CPS" == "" ]];then
                CPS=0
        fi
        if [[ "$OU" == "" ]];then
               OU=0
        fi

        if [[ $health != "OK" ]];then
                status="error"
        fi

        if [[ "$SN" != "" ]];then
                printf "%-16s %-3s %-24s %-5s %-7s %-6s %-7s\n" $2 ${Devlist} ${SN} ${RSC} ${CPS} ${OU} $status>> /home/smartctl_log
        fi

        sync

}


function sata_data_disk()
{
        Devlist=$1
        status="success"
        SN=`smartctl -i -d megaraid,$1 $dev |grep Serial |awk '{print $3}'`
        RSC=`smartctl -A -d megaraid,$1 $dev |grep "5 Reallocate" |awk '{print $10}'`
        CPS=`smartctl -A -d megaraid,$1 $dev |grep Current_Pending_Sector |awk '{print $10}'`
        OU=`smartctl -A  -d megaraid,$1 $dev |grep Offline_Uncorrectable |awk '{print $10}'`

        if [[ "$RSC" == "" ]];then
                RSC=0
        fi
        if [[  "$CPS" == "" ]];then
                CPS=0
        fi
        if [[ "$OU" == "" ]];then
               OU=0
        fi


        if [[ $RSC != 0 ]] || [[ $CPS != 0 ]] || [[ $OU !=  0 ]];then
                status="error"
        fi
	if [[ "$SN" != "" ]];then
                printf "%-16s %-3s %-24s %-5s %-7s %-6s %-7s\n" $2 ${Devlist} ${SN} ${RSC} ${CPS} ${OU} $status>> /home/smartctl_log
        fi

        sync
}

function sas_data_disk()
{
	Devlist=$1
        status="success"
        SN=`smartctl -i -d megaraid,$1 $dev |grep Serial |awk '{print $3}'`
        health=`smartctl -H -d megaraid,$1 $dev |grep Health |awk '{print $4}'`

        if [[ "$RSC" == "" ]];then
                RSC=0
        fi
        if [[  "$CPS" == "" ]];then
                CPS=0
        fi
        if [[ "$OU" == "" ]];then
               OU=0
        fi

        if [[ $health != "OK" ]];then
                status="error"
	fi

        if [[ "$SN" != "" ]];then
                printf "%-16s %-3s %-24s %-5s %-7s %-6s %-7s\n" $2 ${Devlist} ${SN} ${RSC} ${CPS} ${OU} $status>> /home/smartctl_log
        fi

        sync

}

function lsi_data_disk()
{
        Devlist=$1
        status="success"
        disk_type=`smartctl -i -d megaraid,$1 /dev/sdb |grep "Transport" |awk '{print $3}'`
	if [[ "$disk_type" == "SAS" ]];then
		sas_data_disk $Devlist $2
	else
		sata_data_disk $Devlist $2
	fi
}

function nvme_disk()
{
        Devlist=$1
        status="success"
        SN=`smartctl -i /dev/${Devlist} |grep Serial |awk '{print $3}'`
        RSC=`smartctl -A /dev/nvme0n1 |grep "Critical Warning" |awk '{print $3}'`
        CPS=`smartctl -A /dev/nvme0n1 |grep "Media and Data " |awk '{print $6}'`

        if [[ "$RSC" == "" ]];then
                RSC=0
        fi
        if [[  "$CPS" == "" ]];then
                CPS=0
        fi
        if [[ "$OU" == "" ]];then
               OU=0
        fi


        if [[ $RSC != 0x00 ]] || [[ $CPS != 0 ]] || [[ $OU !=  0 ]];then
                status="error"
        fi

	if [[ "$SN" != "" ]];then
        	printf "%-16s %-3s %-24s %-5s %-7s %-6s %-7s\n" $2 ${Devlist} ${SN} ${RSC} ${CPS} ${OU} $status>> /home/smartctl_log
        fi
	sync

}

function nvme_test()
{
        nvmeDevcnt=` cat /proc/partitions | grep -c "nvme" `
        nvmeDevnum=` cat /proc/partitions | grep "nvme" |gawk '{print $4}'`
        for((i=1; i<=$nvmeDevcnt; i++))
        do
                Devlist=`echo $nvmeDevnum | gawk '{print $'$i'}'`
                nvme_disk $Devlist  $1 &
        done
}

date_day=`date`
echo ${date_day} --------------------------------------------------> /home/smartctl_log
printf "%-16s %-3s %-24s %-5s %-7s %-6s %-7s\n" host_ip sdx Serial_Number 5_RSC 197_CPS 198_OU status >> /home/smartctl_log
lspci |grep LSI
RAID_FLAG=`echo $?`
if [[ $RAID_FLAG == 0 ]] ;then
        count="0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 "
        for i in $count
        do
                lsi_data_disk $i $1
        done
	sysytem_disk
	nvme_test $1
else
	sysytem_disk
        nvme_test $1
fi

