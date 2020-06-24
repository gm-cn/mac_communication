#/bin/sh
function crc_test()
{
	sh -x ./extension.sh  crc cds-china   --ip_file=./host_ip
	sh -x ./extension.sh  switch_crc CDS-china1  --ip_file=./switch_ip
}
sh -x ./extension.sh  power_status cds-china  --ip_file=./host_ip
crc_test & 
sh -x ./extension.sh  disk_test cds-china  --ip_file=./host_ip
sh -x ./extension.sh cpu_test cds-china   --ip_file=./host_ip  
sh -x ./extension.sh  mem cds-china --mem_size=255.5G  --ip_file=./host_ip  
sh -x ./extension.sh  power_status cds-china  --ip_file=./host_ip  
sh -x ./extension.sh  power_off cds-china  --ip_file=./host_ip  
