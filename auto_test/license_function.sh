#!/bin/sh
function usage()
{
    
    echo "USAGE: $0 [OPTIONS] < license_view,license_update,timezone_setting,switch_check,check_ip > <password>"
    echo ""
    echo "Available OPTIONS:"
    echo ""
    echo "  --ip_file      <ip_file>   ip list. "
    echo "  --file         <flag_type>   license file "
    echo "  -h, --help      Show the help message."
    echo ""
    exit 0
}

dir=`pwd`
host_ips_file="$dir/host_ips"


function parse_options()
{
    args=$(getopt -o h -l ip_file:,file:,help -- "$@")

    if [[ $? -ne 0 ]];then
        usage >&2
    fi
    
    eval set -- "${args}"
    
    while true
    do
        case $1 in
            --file)
                file=$2
                shift 2
                ;;
            --ip_file)
                ip_file=$2
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
    
    if [[ $# -ne 3 && $# -ne 1 ]]; then
        usage
    fi
    action=$1
    name=$2
    password=$3
}


function is_valid_action()
{
    action=$1
    valid_action=(license_view license_update timezone_setting switch_check check_ip)
    for val in ${valid_action[@]}; do
        if [[ "${val}" == "${action}" ]]; then
            return 0
        fi
    done
    return 1
}

parse_options $@

is_valid_action ${action} || usage
path=`dirname $0`
cmd_dir="/opt/dell/srvadmin/sbin/racadm"
license_view_log="./license_view_log"
license_update_log="./license_update_log"
timezone_setting_log="./timezone_setting_log"
switch_check_log="./switch_check_log"
check_ip_result="./check_ip_result"

function get_host_ip()
{
        if [[ $ip_file != "" ]];then
                host_ips_file=$ip_file
        fi
}

license_view()
{
	racadm_comm="$cmd_dir -r $1 -u $2 -p $3 --nocertwarn"
	status=$($racadm_comm license view |grep  "iDRAC9 Enterprise License" )
	if [[ -z $status ]] ;then
		echo "ipmiip:$1 license:error" >> $license_view_log
    	else
		echo "ipmiip:$1 license:ok" >> $license_view_log
    	fi

}
function function_license_view()
{
	host_number=`cat $host_ips_file |wc -l`
	echo > $license_view_log
        for((n=1;n<=$host_number;n++))
        do
            host_ip=`cat $host_ips_file |sed -n "$n"p |awk '{print $1}'`
            license_view $host_ip $1 $2 
        done

}

license_update()
{
	racadm_comm="$cmd_dir -r $1 -u $2 -p $3 --nocertwarn"
        status=$($racadm_comm license view |grep -w Status |grep -w OK)
        if [[ -z $status ]] ;then
        	sn=`$racadm_comm getsysinfo | grep "Service Tag" | awk '{print $4}' | tr \n \t`
		file_name=`ls * |grep "$sn"`
        	if [[ ! -f $file_name ]];then
            		echo "$i not fount license"
			echo "ipmiip:$1 license file no find" >> $license_update_log
            		return 1
        	fi
        	$racadm_comm license  import -f $file_name -c idrac.embedded.1
		ret=`echo $?`
		if [[ $ret == 0 ]];then
			echo "ipmiip:$1 license update: success" >> $license_update_log
		else
			echo "ipmiip:$1 license update: error" >> $license_update_log
		fi

	else
	            echo "ipmiip:$1 license no update" >> $license_update_log
	    fi
}

function_switch_check()
{
    	let host_number=`cat $host_ips_file | wc -l`
	echo > $switch_check_log
	let host_number++
	for((n=1;n<$host_number;n++))
	do
		host_id=`cat $host_ips_file | sed -n "$n"p | awk '{print $1}'`
		sshortel=`cat $host_ips_file | sed -n "$n"p | awk '{print $3}' | tr 'A-Z' 'a-z' | tr -d "\r"`
		echo $sshortel
		result=$(echo $host_id | grep "S57")
	    	if [[ $? == 1 ]]; then
	        	host_ip=`cat $host_ips_file | sed -n "$n"p | awk '{print $2}'`
			if [[ $sshortel == "ssh" ]]; then
				switch_check_ssh $host_ip $1 $2 $host_id  
			else
				switch_check_tel $host_ip $1 $2 $host_id
			fi
	    	fi
	done
	return 0

}

switch_check_tel()
{
	cmd="display version | include VRP"
	product=`(
                sleep 2;
                echo $name;
                sleep 2;
                echo $password;
                sleep 2;
                echo "$cmd"
                sleep 2;
	) | telnet $1 | grep VRP | awk '{print $6}' | cut -b 2-7 | tr -d "\n"`
	cmd1="display version | include Patch"
	patch=`(
                sleep 2;
                echo $name;
                sleep 2;
                echo $password;
                sleep 2;
                echo "$cmd1"
                sleep 2;
	) | telnet $1 | grep Patch | awk '{print $3}' | tr -d '|' | tr -d "\n" | tr -d "\r"`
	if [[ $product == "" ]]; then
		switch_check_ssh $1 $2 $3 $4
		return 0
	fi	
	#if [[ $product == "CE8800" ]]; then
        #	echo "$4 $1" >> $switch_check_log
        #	return 1
    	#fi

    	#if [[ $product == "CE7800" ]]; then
        #	echo "$4 $1" >> $switch_check_log
        #	return 1
    	#fi

    	#if [[ $product == "CE6800" ]]; then
	#        echo "$4 $1" >> $switch_check_log
        #	return 1
	#fi

	#if [[ $product == "CE5800" ]]; then
        #	echo "$4 $1" >> $switch_check_log
	#       return 1
	#fi

    	#if [[ $patch == "V200R001C00SPC700" ]]; then
        #	echo "$4 $1" >> $switch_check_log
	#       return 1
	#fi

    	#if [[ $patch == "V200R002C50SPC800" ]]; then
        #	echo "$4 $1" >> $switch_check_log
	#        return 1
    	#fi

    	#if [[ $patch == "V200R003C00SPC810" ]]; then
        #	echo "$4 $1" >> $switch_check_log
        #	return 1
    	#fi
	echo "version is $product, patch version is $patch, ip address is $1, product number is $4" >> $switch_check_log
    	return 0	


}

switch_check_ssh()
{
    ssh="sshpass -p $password ssh -o StrictHostKeyChecking=no cdsadmin@$1"
    local product=`$ssh "display version | include VRP" | grep VRP | awk '{print $6}' | cut -b 2-7`
    local patch=`$ssh "display version | include Patch" | grep Patch | awk '{print $3}' | tr -d "\r"`
    echo "version is $product, patch version is $patch, ip address is $1, product number is $4" >> $switch_check_log
     
    if [[ $product == "" ]]; then
	switch_check_tel $1 $2 $3 $4
	return 0
    fi
   
    #if [[ $product == "CE8800" ]]; then
    #    echo "$4 $1" >> $switch_check_log
    #    return 1
    #fi

    #if [[ $product == "CE7800" ]]; then
    #    echo "$4 $1" >> $switch_check_log
    #    return 1
    #fi

    #if [[ $product == "CE6800" ]]; then
    #    echo "$4 $1" >> $switch_check_log
    #    return 1
    #fi

    #if [[ $product == "CE5800" ]]; then
    #    echo "$4 $1" >> $switch_check_log
    #    return 1
    #fi

    #if [[ $patch == "V200R001C00SPC700" ]]; then
    #    echo "$4 $1" >> $switch_check_log
    #    return 1
    #fi

    #if [[ $patch == "V200R002C50SPC800" ]]; then
    #    echo "$4 $1" >> $switch_check_log
    #    return 1
    #fi

    #if [[ $patch == "V200R003C00SPC810" ]]; then
    #    echo "$4 $1" >> $switch_check_log
    #    return 1
    #fi

    return 0
}

working_switch_check()
{
    ssh="sshpass -p $password ssh -o StrictHostKeyChecking=no cdsadmin@$1"
    local product=`$ssh "display version | include VRP" | grep VRP | awk '{print $6}' | cut -b 2-7`
    local patch=`$ssh "display version | include Patch" | grep Patch | awk '{print $3}'`
    if [[ $product == "CE8800" ]]; then
        echo "$4 $1" >> $switch_check_log
        return 1
    fi

    if [[ $product == "CE7800" ]]; then
        echo "$4 $1" >> $switch_check_log
        return 1
    fi

    if [[ $product == "CE6800" ]]; then
        echo "$4 $1" >> $switch_check_log
        return 1
    fi

    if [[ $product == "CE5800" ]]; then
        echo "$4 $1" >> $switch_check_log
        return 1
    fi

    if [[ $patch == "V200R001C00SPC700" ]]; then
        echo "$4 $1" >> $switch_check_log
        return 1
    fi

    if [[ $patch == "V200R002C50SPC800" ]]; then
        echo "$4 $1" >> $switch_check_log
        return 1
    fi

    if [[ $patch == "V200R003C00SPC810" ]]; then
        echo "$4 $1" >> $switch_check_log
        return 1
    fi

    return 0
}

function_timezone_setting()
{
	host_number=`cat $host_ips_file | wc -l`
	echo > $timezone_setting_log
	for((n=1;n<=$host_number;n++))
	do
		host_ip=`cat $host_ips_file | sed -n "$n"p | awk '{print $1}'`
		timezone_setting $host_ip $1 $2
	done
}
timezone_setting()
{
    racadm_comm="$cmd_dir -r $1 -u $2 -p $3 --nocertwarn"
    $racadm_comm get idrac.time | grep Shanghai
    if [[ $? == 0 ]]; then
        echo "Time zone already China"
    else
        echo "changing time zone to Asia/Shanghai"
        $racadm_comm set idrac.time.timezone Asia/Shanghai
        $racadm_comm set idrac.time.timezoneoffset 480
	$racadm_comm get idrac.time | grep Shanghai
        if [[ $? == 0 ]]; then
		echo "change time zone success" >> $timezone_setting_log	
	else
		echo "change time zone error ">> $timezone_setting_log
	fi
    fi
}

function function_license_update()
{
	host_number=`cat $host_ips_file |wc -l`
        echo > $license_update_log
        for((n=1;n<=$host_number;n++))
        do
            host_ip=`cat $host_ips_file |sed -n "$n"p |awk '{print $1}'`
            license_update $host_ip $1 $2
        done

}

check_ip()
{
	sn=`ipmitool -U $1 -P $2 -H $3 -I lanplus fru | grep "Product Serial" | awk '{print $4}'`
	echo "host ip is $3, serial number is $sn" >> $check_ip_result
}

function function_check_ip()
{
	host_number=`cat $host_ips_file | wc -l`
	echo "" > $check_ip_result
	for ((n=1;n<=$host_number;n++))
	do
		ip=`cat $host_ips_file | sed -n "$n"p | awk '{print $1}'`
		ip_username=`cat $host_ips_file | sed -n "$n"p | awk '{print $2}'`
		ip_password=`cat $host_ips_file | sed -n "$n"p | awk '{print $3}'`
		check_ip $ip_username $ip_password $ip
	done
}


case "${action}" in
    license_view)
	get_host_ip 
        function_license_view $name $password
        ;;
    license_update)
	get_host_ip
        function_license_update $name $password
        ;;
    timezone_setting)
    get_host_ip
        function_timezone_setting $password
        ;;
    switch_check)
    get_host_ip
        function_switch_check $name $password
        ;;
	check_ip)
	get_host_ip
		function_check_ip 
		;;

    *)
        echo "Unknown Action:${action}!"
        usage
        ;;
esac

