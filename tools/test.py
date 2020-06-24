import re
from netmiko import ConnectHandler
from netmiko.huawei.huawei_ssh import HuaweiSSH
import datetime

# huawei = {
#     "device_type": "huawei",
#     "ip": "10.177.178.241",
#     "username": "admin-ssh",
#     "password": "CDS-china1"
# }
#
# ssh = None
# try:
#     print "==="
#     print "start connection:", datetime.datetime.now()
#     print "==="
#     ssh = HuaweiSSH(**huawei)
#     print "==="
#     ssh.config_mode()
#     print "==="
#     set_vlan = ["interface 10GE1/0/43", "port default vlan 1000", "port link-type access", "commit", "q", "q"]
#     output = ""
#     for cmd in set_vlan:
#         output += ssh.send_config_set(cmd, exit_config_mode=False)
#     print output
#     print super(HuaweiSSH, ssh).save_config(cmd='save', confirm=True, confirm_response='Y')
#
# finally:
#     ssh.disconnect()
#     print "end connection:", datetime.datetime.now()


# def get_relations(special_vlan=None, special_mac=[]):
#     relations = []
#     pattern = re.compile(r'\S+')
#     if len(special_mac) > 0:
#         for item in special_mac:
#             datas = net_connect.send_command("display mac-address %s" % item)
#             for line in datas.split("\n")[7:-2]:
#                 data = pattern.findall(line)
#                 mac = ":".join(i[0:2] + ":" + i[2:4] for i in data[0].split("-"))
#                 relations.append({"mac": mac, "port": data[2]})
#
#     if special_vlan:
#         datas = net_connect.send_command("display mac-address vlan %s" % special_vlan)
#         for line in datas.split("\n")[7:-2]:
#             data = pattern.findall(line)
#             mac = ":".join(i[0:2] + ":" + i[2:4] for i in data[0].split("-"))
#             relations.append({"mac": mac, "port": data[2]})
#
#     return relations
#
# print get_relations(special_mac=["6c92-bf62-ab9e", "6c92-bf62-aa09"])
# print datetime.datetime.now()

# print net_connect.send_command('disp clock')
# display_interface = ["interface 10GE1/0/12", "display this"]
# print net_connect.send_config_set(display_interface)

# set_vlan = ["interface 10GE1/0/12", "port default vlan 2000", "port link-type access", "commit", "q", "q", "save", "Y"]
# command1 = ['qos car 12345678-50 cir 82944 kbps', 'commit',
#             'interface 10GE1/0/11', 'port default vlan 2222',
#             'port link-type access', 'qos car inbound 12345678-50',
#             'qos lr cir 51200 kbps cbs 102400 kbytes outbound',
#             'undo shutdown', 'q', 'qos car 12345678-100 cir 165888 kbps',
#             'commit', 'interface 10GE1/0/12', 'port default vlan 2223',
#             'port link-type access', 'qos car inbound 12345678-100',
#             'qos lr cir 102400 kbps cbs 204800 kbytes outbound',
#             'undo shutdown', 'q', 'commit', 'q']
# ssh.config_mode()
# output = ''
# for cmd in command1:
#     output += ssh.send_config_set(cmd, exit_config_mode=False)
# print output
#
# print ssh.save_config(confirm=True, confirm_response='Y')
# command2 = ["commit"]
# print net_connect.send_config_set(command2)
# print "end execute", datetime.datetime.now()
# ssh.disconnect()
# print "end disconnect", datetime.datetime.now()
# print "***"
# print "exit"

# print result.split("\n")
#
# pattern = re.compile(r'\S+')
# for line in result.split("\n")[7:-2]:
#     print "***"
#     data = pattern.findall(line)
#     mac = data[0]
#     vlan = data[1].split("/")[0]
#     port = data[2]
#     print "mac:", mac
#     print "vlan:", vlan
#     print "port:", port
#
#
# import telnetlib
#
# import re
#
#
# # def main():
# #     session = telnetlib.Telnet("10.177.178.241", 23, 10)
# #     session.set_debuglevel(2)
# #     session.read_until("Username:")
# #     session.write("admin123" + '\n')
# #     session.read_until('Password:')
# #     session.write("CDS-china1" + '\n')
# #     command = ['system-view', 'interface 10GE1/0/12', 'display this']
# #     result = ""
# #     try:
# #         for i in command:
# #             session.write(i + '\n')
# #         print session.read_very_eager()
# #     finally:
# #         print "session close"
# #         session.close()
# #     return result
# #
# #
# # print main()
#
# #
# # test = "testaaabbb123"
# # A = "#\ninterface 10GE1/0/12"
# # B = "#\nreturn"
# #
# #
# # if result.find(A):
# #     print "enter"
# #     startIndex = result.find(A)
# #     if result.find(B) > startIndex:
# #         endIndex = result.find(B) + len(B)
# #         result = result[startIndex:endIndex]
#
# # print "******"
# # #
# # # str1 = '# interface 10GE1/0/12 eth-trunk 5 qos lr cir 20480 kbps cbs 40960 kbytes outbound device transceiver 10GBASE-FIBER # return'
# #
# # p = re.compile(r'[#](.*?)[#]')
# #
# # print (re.findall(p, result))


# meta_data = {
#     "hostname": "baremetal",
#     "meta": {
#         "admin_pass": "CDS-china1"
#     },
#     "network_config":
#         {
#             "content_path": "/content/0000"
#
#         },
#     "uuid": "e6c0faca-fd55-44a7-8bda-2ea4e7e5311c"
# }
#
# network_config = meta_data.get('network_config')
#
# print network_config["content_path"].split("/")[-1]
