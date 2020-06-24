#!/bin/sh
automated_testing_log="./automated_testing_log"

echo > $automated_testing_log

for((n=1;n<2;n++))
do
	date_info=`date`
	echo "start automated_testing date:$date_info count:$n"  >> $automated_testing_log
	echo "start pxe_image date:$date_info count:$n" >> $automated_testing_log
	rm tools/test_auto/test.db -f
	rm auto_test/host_ip*  -f
	rm tools/test_auto/pxe_log -f
	rm tools/test_auto/create_bms.log -f
	rm tools/test_auto/success -f
	cd tools/test_auto/
	python notify.py  &
	sleep 30
	python open_bms.py
	cd  ../../
        date_info=`date`
	cat tools/test_auto/pxe_log  |grep error  >> $automated_testing_log
	cat tools/test_auto/create_bms.log  |grep hardware |grep  error >> $automated_testing_log
	echo "end pxe_image date:$date_info count:$n" >> $automated_testing_log
	echo "start crc cpu mem disk power date:$date_info count:$n" >> $automated_testing_log
	cd auto_test/
	sleep  300
	sh -x ./extension_test.sh
	cd ../
	date_info=`date`
	echo "end crc date:$date_info count:$n" >> $automated_testing_log
	cat auto_test/auto_network_test_log |grep ERROR >> $automated_testing_log
	echo "end cpu date:$date_info count:$n" >> $automated_testing_log
	cat auto_test/auto_cpu_log |grep ERROR >> $automated_testing_log
	echo "end mem date:$date_info count:$n" >> $automated_testing_log
	cat auto_test/auto_mem_log |grep ERROR >> $automated_testing_log
	echo "end disk power date:$date_info count:$n" >> $automated_testing_log
	cat auto_test/auto_disk_test_log |grep ERROR >> $automated_testing_log
	echo "end power date:$date_info count:$n" >> $automated_testing_log
	cat auto_test/auto_device_status_log |grep ERROR >> $automated_testing_log
	echo "end crc cpu mem disk power date:$date_info count:$n" >> $automated_testing_log
	echo "end automated_testing date:$date_info count:$n" >> $automated_testing_log
done
