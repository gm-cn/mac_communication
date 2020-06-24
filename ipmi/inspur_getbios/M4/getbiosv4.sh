#!/bin/bash
solcmd=""
COOKIE=""
BMCHOST=$3
                BMCUSER=$4
                BMCPASS=$5

dir=`pwd`
function usage()
{
#cat<<EOF
echo -n ./getbios 
echo ' [$bmcIP] [$user] [$password] [options]
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
                   	      $dir/biosinfo $args  "$biositem"
		  else
			for i in 0x00 0x12 0x13 0x16 0x17 0x18 0x19 0x1b 0x1c 0x20 0x24 0x65 0x05 0x06 0x07 0x08 0x2a 0x2b \
				 0x2d 0x2e 0x2f 0x60 0x61 0x64 0x67 0x68 0x69
		            do
			      $dir/biosinfo $args "$i"
			done   
		  fi
		;;
             -set)
		  if [ ! "x$biosvalue" = "x" ]
		     then
 		  	$dir/biosinfo  $args  "$biositem"  $biosvalue
		  else
		     echo "The $biositem Value needed!"                  		  
		  fi

		;;
             *)
               usage 
              ;;
       esac 

