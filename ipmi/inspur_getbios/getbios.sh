#!/bin/bash
 dir=`pwd`
 if [ $# -lt 4 ]
           then
                ARGstart="$1"
                args=""
                #usage $dir/../instool.sh
                #exit
                arg=""
 		biositem="$2"
		biosvalue="$3"
        else
                ARGstart="$4"
                args="$1 $2 $3"
                arg="-I lanplus -H $1 -U $2 -P $3"
		biositem="$5"
		biosvalue=$6
 fi

 ipmitool $arg  raw 0x3c 0x02 0x02 0xff 0xff  2>/dev/null  >/dev/null
 if [ $? -eq 0 ]; then
    cd $dir/M5
    ./getbiosv5.sh $args $ARGstart "$biositem" $biosvalue
    cd ..
 else
   cd $dir/M4
   ./getbiosv4.sh $args $ARGstart "$biositem" $biosvalue
   cd ..
fi
#ipmitool $args $ARGstart $biositem $biosvalue
