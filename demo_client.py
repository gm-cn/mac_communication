import socket
import struct
import binascii
import netifaces
from functools import reduce
from queue import Queue
import threading
import time
from os.path import getsize
import math
import base64
import copy

ETH_P_BMS = 0x7fff
ETH_P_VLAN = 0x8100
BuffSize = 65536
AF_PACKET = 17

VAR_PACKET = {
    "ver": None,
    "ptype": None,
    "seskey": None,
    "sequence": None,
    "count": None,
    "offset": None,
    "data": None
}

CRL_PACKET = {
    "ver": None,
    "ptype": None,
    "type": None,
    "seskey": None,
    "length": None,
    "data": None
}


class Demo(object):
    def __init__(self):
        self.q = self.create_queue()
        self.var_packet = VAR_PACKET
        self.crl_packet = CRL_PACKET
        self.dst_mac = 'b4:96:91:33:8a:d8'
        self.src_mac = '92:64:af:c3:31:dd'
        self.vlan = '1740'
        self.card = "net1"
        self.file_path = "/home/test.tar.gz"
        self.default_interval_length = 300
        self.default_packet_length = 150

    def create_queue(self):
        q = Queue()
        return q

    def run(self):
        self.q = self.create_queue()
        ack_packet = self.var_packet
        ack_packet["ver"], ack_packet["ptype"] = 1, 0
        self.q.put(ack_packet)
        self.recv_frame()

    def run_f(self):

        self.q = self.create_queue()
        file_length = self.get_size(self.file_path)
        file_sequence = math.ceil(file_length / self.default_interval_length)
        file_end = file_length % self.default_interval_length
        seskey = "No3-seskey"

        if file_end:
            for i in range(file_sequence-1):
                t = threading.Thread(target=self.cut_file, args=(i,self.file_path,seskey,self.default_interval_length,))
                t.start()
            self.cut_file(file_sequence-1, self.file_path, seskey, file_end)
        else:
            for i in range(file_sequence):
                t = threading.Thread(target=self.cut_file, args=(i,self.file_path,seskey,self.default_interval_length,))
                t.start()
        for i in range(file_sequence):
            t = threading.Thread(target=self.send_file)
            t.start()
        self.recv_frame()

    def cut_file(self, file_sequence, file_path, seskey, interval_length):
        var_packet = self.var_packet
        file_count = math.ceil(interval_length / self.default_packet_length)
        offset = 0
        f = open(file_path, "rb")
        f.seek(file_sequence * self.default_interval_length)
        for i in range(file_count):
            var_packet["ver"], var_packet["ptype"], var_packet["seskey"], var_packet["sequence"], var_packet["count"], \
            var_packet["offset"], var_packet["data"] = 1, 1, seskey, file_sequence, 200, offset, f.read(self.default_packet_length)
            offset += 1
            aa = copy.deepcopy(var_packet)
            self.q.put(aa)
        f.close()

    def send_file(self):
        while True:
            print("------------------------------------------------------")
            if not self.q.empty():
                ack_packet = self.q.get()
                ack_packet = str(ack_packet)
                dst_mac = self.dst_mac
                src_mac = self.src_mac
                raw_socket = self.set_socket()
                self.send_packet(raw_socket, self.card, dst_mac, src_mac, ack_packet)
                print(ack_packet)
            else:
                break

    def recv_frame(self):
        raw_socket = socket.socket(socket.PF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_BMS))
        while True:
            if not self.q.empty():
                ack_packet = self.q.get()
                ack_packet = str(ack_packet)
                dst_mac = self.dst_mac
                src_mac = self.src_mac
                self.send_frame(self.card, dst_mac, src_mac, ack_packet)
            packet, packet_info = raw_socket.recvfrom(BuffSize)
            ethHeader = packet[0:14]
            eth_hdr = struct.unpack("!6s6s2s", ethHeader)
            local_mac, src_mac, eth_type = binascii.hexlify(eth_hdr[0]), binascii.hexlify(eth_hdr[1]), \
                                           binascii.hexlify(eth_hdr[2])
            data = packet[14:]
            print(time.asctime(time.localtime(time.time())))
            print("dst mac: {}".format(local_mac))
            print("src mac: {}".format(src_mac))
            print("ethernet type: {}".format(eth_type))
            print("data: {}".format(data.decode("utf-8")))

            rece_data = eval(data)

            if rece_data["ptype"] == 0:
                pass
            elif rece_data["ptype"] == 1:
                pass
            elif rece_data["ptype"] == 2:
                ack_packet = self.var_packet
                ack_packet["ver"], ack_packet["ptype"], ack_packet["seskey"], ack_packet["data"] = 1, 1, rece_data[
                    "seskey"], "Hello KangKang, i'm Jan"
                ack_packet = str(ack_packet)
                dst_Mac = src_mac.decode("utf-8")
                src_Mac = local_mac.decode("utf-8")
                self.send_frame(self.card, dst_Mac, src_Mac, ack_packet)
            elif rece_data["ptype"] == 3:
                pass

    def send_vlan_frame(self, net_card, dst_mac, src_mac, vlan, data='hello'):
        raw_socket = socket.socket(socket.PF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_BMS))
        raw_socket.bind((net_card, socket.htons(ETH_P_BMS)))

        bytes_srcmac = self.format_mac_bytes(self.format_mac(src_mac))
        bytes_dstmac = self.format_mac_bytes(self.format_mac(dst_mac))
        bytes_vlan = self.format_mac_bytes(self.i2b_hex(vlan))
        ETH_P_VLAN_BY = self.format_mac_bytes(self.i2b_hex(ETH_P_VLAN))
        ETH_P_BMS_BY = self.format_mac_bytes(self.i2b_hex(ETH_P_BMS))

        vlan_tag = struct.pack("!2s2s", ETH_P_VLAN_BY, bytes_vlan)
        packet = struct.pack("!6s6s4s2s", bytes_dstmac, bytes_srcmac, vlan_tag, ETH_P_BMS_BY)

        raw_socket.send(packet + data.encode('utf8'))


    def set_socket(self):
        raw_socket = socket.socket(socket.PF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_BMS))
        return raw_socket


    def send_packet(self, raw_socket, net_card, dst_mac, src_mac, data='hello'):
        raw_socket.bind((net_card, socket.htons(ETH_P_BMS)))

        bytes_srcmac = self.format_mac_bytes(self.format_mac(src_mac))
        bytes_dstmac = self.format_mac_bytes(self.format_mac(dst_mac))
        ETH_P_BMS_BY = self.format_mac_bytes(self.i2b_hex(ETH_P_BMS))

        packet = struct.pack("!6s6s2s", bytes_dstmac, bytes_srcmac, ETH_P_BMS_BY)

        raw_socket.send(packet + data.encode('utf8'))


    def send_frame(self, net_card, dst_mac, src_mac, data='hello'):
        raw_socket = socket.socket(socket.PF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_BMS))
        raw_socket.bind((net_card, socket.htons(ETH_P_BMS)))

        bytes_srcmac = self.format_mac_bytes(self.format_mac(src_mac))
        bytes_dstmac = self.format_mac_bytes(self.format_mac(dst_mac))
        ETH_P_BMS_BY = self.format_mac_bytes(self.i2b_hex(ETH_P_BMS))

        packet = struct.pack("!6s6s2s", bytes_dstmac, bytes_srcmac, ETH_P_BMS_BY)

        raw_socket.send(packet + data.encode('utf8'))

    def format_mac(self, mac_address):
        return mac_address.replace(":", "")
        # return ':'.join(mac_address[i:i + 2] for i in range(0, len(mac_address), 2))

    def format_mac_bytes(self, msg):
        return reduce(lambda x, y: x + y, [binascii.unhexlify(msg[i:i + 2]) for i in range(0, len(msg), 2)])

    def i2b_hex(self, protocol):
        b_protocol = hex(int(protocol))[2:]
        return b_protocol if len(b_protocol) % 2 == 0 else '0{0}'.format(b_protocol).encode('utf8')

    def get_size(self, file_path):
        return getsize(file_path)

    def get_net(self, local_mac):
        net_list = []
        for i in netifaces.interfaces():
            if i == "lo":
                continue
            else:
                mac = netifaces.ifaddresses(i)[AF_PACKET][0]["addr"]
                if self.format_mac(local_mac) == mac:
                    net_list.append(i)
        return net_list


if __name__ == '__main__':
    # 修改网卡名， mac， vlan
    a = Demo()
    a.run_f()
