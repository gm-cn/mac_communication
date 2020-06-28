#!/bin/bash

dir=`pwd`
function usage()
{
#cat<<EOF
echo -n getbios.sh 
echo ' [$bmcIP] [$user] [$password]  [options]
options:
       	-h       get help 
       	-get     get bios info [options]
                 "bios item name"
		 all
		 exp:
		 -get "Hyper Threading Technology"
		 -get all
       	-set     set bios [options]
		 [bios item name] [value]
		 exp:
		 -set "Hyper Threading Technology" disable
'
exit 128

}

#######################################################################################################
#main()
        args=`echo $args | awk '{for(i=2;i<20;i++)print $i;}'`
        if [ $# -lt 4 ]
           then
                ARGstart="$1"
                args=""
                #usage $dir/../instool.sh
                #exit
                biositem="$2"
                biosvalue="$3"
        else
                ARGstart="$4"
                args="-I lanplus -H $1 -U $2 -P $3"
                biositem="$5"
                biosvalue=$6
        fi

        case $ARGstart in
             -h)
              usage $0
                ;;
 	     -get)
		  if [  "x$biositem" = "x" ]
                        then
			echo "bios -get must be  all|\$VALUE"
			exit
		  fi
                  if [ ! "x$biositem" = "xall" ]
			then
                   	      $dir/biosinfo "$args"  "$biositem"
		  else
			for i in 0x0021 0x0022 0x0023 0x0024 0x002A 0x002D 0x002E 0x002F 0x0030 0x0031 0x0032 0x0033 0x0034 0x0035\
				 0x0037 0x0038 0x003A 0x003d 0x0046 0x0047 0x0056 0x0065 0x0068 0x00c4 0x00c5 0x00c8 0x00c9 0x00ca 0x00cb\
                                 0x00cc 0x00cd 0x00ce 0x00cf 0x00d0 0x00d3 0x00dc 0x00DD 0x0176 0x0177 0x019B 0X0183 0x01A7 0x01e3 0x01e4 0x01e5 0x01e6 0x01e7 0x01e8\
                                 0x01e9 0x01ea 0x01eb 0x01ec 0x01ed 0x01ee 0x01ef 0x01f5 0x01fb 0x01fc 0x0205 0x0211 0x0212 0x0213\
                                 0x0214 0x0215  
                           do 
			      $dir/biosinfo "$args" "$i"
			done   
		  fi
		;;
             -set)
                  case $biositem in 
                  group)
                     
                     case $biosvalue in
                        legacy)
                             ./getbiosv5.sh -set "CSM Boot Mode" legacy
                             ./getbiosv5.sh -set "CSM Network" legacy 
                             ./getbiosv5.sh -set "CSM Storage" legacy 
                             ./getbiosv5.sh -set "CSM Video OPROM Policy" legacy
                             ./getbiosv5.sh -set "CSM Other PCI devices" legacy

                            ;;
                        uefi)
                            ./getbiosv5.sh -set "CSM Boot Mode" uefi
                             ./getbiosv5.sh -set "CSM Network"  uefi
                             ./getbiosv5.sh -set "CSM Storage"  uefi
                             ./getbiosv5.sh -set "CSM Video OPROM Policy" uefi
                             ./getbiosv5.sh -set "CSM Other PCI devices"  uefi
                            ;;                     
                        perf)
                            ./getbiosv5.sh -set "SpeedStep"     enable
                             ./getbiosv5.sh -set "turbo"        enable
                             ./getbiosv5.sh -set "Uncore Freq Scaling"  max
                             ./getbiosv5.sh -set "C-State" disable
                             ./getbiosv5.sh -set "CPU C6 report"  disable
                             ./getbiosv5.sh -set "C1E"  disable 
                             ./getbiosv5.sh -set "Package C State" C0
                             ./getbiosv5.sh -set "ENERGY_PERF_BIAS_CFG" 0
                             ./getbiosv5.sh -set "Monitor" disable
                             ./getbiosv5.sh -set "Performance Profile" custom
                             ./getbiosv5.sh -set "PCI-E ASPM Support"  disable
                            ;;
                        energy)
                             ./getbiosv5.sh -set "SpeedStep"     enable
                             ./getbiosv5.sh -set "turbo"         disable
                             ./getbiosv5.sh -set "Uncore Freq Scaling"  enable
                             ./getbiosv5.sh -set "C-State" enable
                             ./getbiosv5.sh -set "CPU C6 report"      enable             
                             ./getbiosv5.sh -set "C1E"     enable
                             ./getbiosv5.sh -set "Package C State" Limit
                             ./getbiosv5.sh -set "ENERGY_PERF_BIAS_CFG" "Balanced Power"
                             ./getbiosv5.sh -set "Monitor"  enable
                             ./getbiosv5.sh -set "Performance Profile" custom
                             ./getbiosv5.sh -set "PCI-E ASPM Support"  Per
                            ;;
                        *)
                         echo "The group args must be in legacy|uefi|perf|energy"
                        ;;
                     esac
                   ;;
                   *)
		  if [ ! "x$biosvalue" = "x" ]
		     then
 		  	$dir/biosinfo  "$args"  "$biositem"  "$biosvalue"
		  else
		     echo "The $biositem Value needed!"                  		  
		  fi
                     ;;
                  esac
		;;
             *)
               echo $ARGstart
               usage 
              ;;
       esac 

