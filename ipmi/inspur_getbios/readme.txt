#SA5212M4 SA5280M4 SA5112M4
##SA5212M5 and NF5280M5
V5.0.4 2018-6-20
1. add new function for 5280M5/5180M5
   -set group legacy|uefi|perf|energy
   exp:
       ./getbios.sh -set group legacy
       ./getbios.sh $bmcip $bmcuser $bmcpasswd -set group perf


V5.0.3
1. bug recovrey,function raw error!
2. bug recovery,bios value set error when value num >2


V5.0.1
1.get all the bios items in the configure.txt
2.set bios,needed make sure first the bios surppoted !

       -get     get bios info [options]
                 "bios item name"
		 all
		 exp:
		 -get "Hyper-Threading"
		 -get all
       	-set     set bios [options]
		 [bios item name] [value]
		 exp:
		 -set "Hyper-Threading" disable

or
when too many bios items ,
1)cat M5/configurev5.txt | grep -i "Numa" 
  0x00D3:Numa:0 = Disabled:Reserved (Chip)
  0x00D3:Numa:1 = Enabled:Reserved (Chip)
  0x01EF:Workload Configuration:1 = NUMA:Socket 1
  0x01F6:Sub NUMA Clustering:0 = Disabled:Socket 1
  0x01F6:Sub NUMA Clustering:1 = Enabled:Socket 1
  0x01F6:Sub NUMA Clustering:2 = Auto:Socket 1

2)./getbios -get 0x00d3 
  ./getbios $bmcip $username $password -get 0x00d3
  Numa       : Enable
3)./getbios -set 0x00d3 Disab
  ./getbios $bmcip $username $password -set 0x00D3 Enabled

