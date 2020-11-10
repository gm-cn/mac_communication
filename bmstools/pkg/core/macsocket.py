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
from time import sleep

from .packet import Frame
from .packet import ControlPacket

import logging

ETH_P_BMS = 0x7fff
ETH_P_VLAN = 0x8100
BuffSize = 65536
TCP_PROTOCOL = 17

logger = logging.getLogger(__name__)


class MACSocket(object):

    def __init__(self):
        self.net_card = None
        self.receive_socket = socket.socket(socket.PF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_BMS))
        self.ETH_P_BMS_BY = None
        self.ETH_P_VLAN_BY = None
        self.default_interval_length = 900000
        self.default_packet_length = 300
        self.src_mac = None
        self.packet_list = {"client_key": {"num": None}}
        self.server_packet_list = []

    def set_send_socket(self):
        raw_socket = socket.socket(socket.PF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_BMS))
        raw_socket.bind((self.net_card, socket.htons(ETH_P_BMS)))
        return raw_socket

    def receive_frame(self):
        """
        二层接收帧数据包Frame，接收之后返回ACK
        """
        packet, packet_info = self.receive_socket.recvfrom(BuffSize)
        eth_header = packet[0:14]
        eth_hdr = struct.unpack("!6s6s2s", eth_header)
        local_mac, src_mac, eth_type = binascii.hexlify(eth_hdr[0]), binascii.hexlify(eth_hdr[1]), binascii.hexlify(
            eth_hdr[2])
        data = eval(packet[14:])
        return local_mac, src_mac, data

    def send_frame(self, dst_mac, src_mac, data, raw_socket):
        """
        二层发送帧数据包Frame，记录发送的数据，并超时重试
        """
        packet = struct.pack("!6s6s2s", dst_mac, src_mac, self.ETH_P_BMS_BY)
        raw_socket.send(packet + data.encode('utf8'))

    def send_vlan_frame(self, b_vlan, dst_mac, src_mac, data, raw_socket):
        vlan_tag = struct.pack("!2s2s", self.ETH_P_VLAN_BY, b_vlan)
        packet = struct.pack("!6s6s4s2s", dst_mac, src_mac, vlan_tag, self.ETH_P_BMS_BY)
        raw_socket.send(packet + data.encode('utf8'))

    def receive_data(self):
        """
        一个sequence中接收的数据，并排序重组，返回Packet
        """
        packet = self.receive_frame()
        local_mac, src_mac, data = packet[0], packet[1], packet[2]
        if data["ptype"] == 1:
            self.server_packet_list.append(data)
            if len(self.server_packet_list) == data["count"]:
                self.server_packet_list.sort(key=lambda x: (x["sequence"], x["offset"]))
                data["data"] = reduce(lambda x, y: x + y, [i["data"] for i in self.server_packet_list])
                return local_mac, src_mac, data
        elif data["ptype"] == 2 and data["sequence"]:
            """
            resend packet
            """
            client_key, sequence, count, offset = data["client_key"], data["sequence"], data["count"], data["offset"]
            try:
                self.packet_list[client_key].pop(sequence * count + offset)
            except Exception as exc:
                logger.error("receive data error: %s" % exc, exc_info=True)
        elif data["ptype"] == 2 and data["sequence"] is None:
            """
            握手包
            """
            return local_mac, src_mac, data
        elif data["ptype"] == 3:
            return local_mac, src_mac, data
        elif data["ptype"] == 0:
            return local_mac, src_mac, data
        elif data["ptype"] == 255:
            return local_mac, src_mac, data

    def send_data(self, dst_mac, sequence, server_key, data, client_key, vlan, raw_socket):
        """
        发送sequence数据Packet，并拆分为帧包，所有数据都收到ACK，才算发送完成
        """
        var_packet = Frame()
        bytes_srcmac = self.format_mac_bytes(self.format_mac(self.src_mac))
        bytes_dstmac = self.format_mac_bytes(self.format_mac(dst_mac))
        bytes_vlan = self.format_mac_bytes(self.i2b_hex(vlan))

        count = math.ceil(len(data) / self.default_packet_length)

        var_packet.ptype, var_packet.client_key, var_packet.server_key, var_packet.sequence, var_packet.count = 1, \
                                                                                client_key, server_key, sequence, count
        for i in range(count):
            var_packet.offset, var_packet.data = i, data[
                                                    i * self.default_packet_length:(i + 1) * self.default_packet_length]
            self.send_vlan_frame(b_vlan=bytes_vlan, dst_mac=bytes_dstmac, src_mac=bytes_srcmac,
                                 data=str(var_packet.__dict__),
                                 raw_socket=raw_socket)
            self.packet_list[client_key][sequence * count + i] = var_packet.__dict__
        sleep(1)
        if len(self.packet_list[client_key]) != 0:
            for i in self.packet_list[client_key]:
                self.send_vlan_frame(b_vlan=bytes_vlan, dst_mac=bytes_dstmac, src_mac=bytes_srcmac,
                                     data=str(self.packet_list[client_key][i]), raw_socket=raw_socket)

    def send_func_packet(self, dst_mac, ptype, server_key=None, client_key=None, data=None, vlan=None, raw_socket=None):
        var_packet = Frame()
        self.ETH_P_BMS_BY = self.format_mac_bytes(self.i2b_hex(ETH_P_BMS))
        self.ETH_P_VLAN_BY = self.format_mac_bytes(self.i2b_hex(ETH_P_VLAN))
        bytes_srcmac = self.format_mac_bytes(self.format_mac(self.src_mac))
        bytes_dstmac = self.format_mac_bytes(self.format_mac(dst_mac))
        bytes_vlan = self.format_mac_bytes(self.i2b_hex(vlan))

        if ptype == 0:
            var_packet.ptype, var_packet.client_key, var_packet.server_key, var_packet.vlan = 0, client_key, \
                                                                                              server_key, vlan
        elif ptype == 2:
            var_packet.ptype, var_packet.client_key, var_packet.server_key, var_packet.vlan = 2, client_key, \
                                                                                              server_key, vlan
        elif ptype == 3:
            var_packet.ptype, var_packet.client_key, var_packet.server_key, var_packet.data, var_packet.vlan = 3, \
                                                                                                               client_key, server_key, data, vlan
        elif ptype == 255:
            var_packet.ptype, var_packet.client_key, var_packet.server_key, var_packet.data, var_packet.vlan = 255, \
                                                                                                               client_key, server_key, data, vlan

        self.send_vlan_frame(b_vlan=bytes_vlan, dst_mac=bytes_dstmac, src_mac=bytes_srcmac,
                             data=str(var_packet.__dict__),
                             raw_socket=raw_socket)

    def open_session(self):
        """
        客户端发送开启一个session
        """
        pass

    def ack_open_session(self):
        """服务端确认开启session"""
        pass

    def close_session(self):
        """
        客户端发送关闭session
        """
        pass

    def ack_close_session(self):
        """服务端确认关闭session"""
        pass

    def format_mac(self, mac_address):
        return mac_address.replace(":", "")

    def format_mac_bytes(self, msg):
        return reduce(lambda x, y: x + y, [binascii.unhexlify(msg[i:i + 2]) for i in range(0, len(msg), 2)])

    def i2b_hex(self, protocol):
        b_protocol = hex(int(protocol))[2:]
        return b_protocol if len(b_protocol) % 2 == 0 else '0{0}'.format(b_protocol).encode('utf8')

    def get_net(self, local_mac):
        net_list = []
        for i in netifaces.interfaces():
            if i == "lo" and "bond" in i:
                continue
            else:
                mac = netifaces.ifaddresses(i)[TCP_PROTOCOL][0]["addr"]
                if local_mac == self.format_mac(mac):
                    net_list.append(i)
        return net_list

    def get_mac(self, card):
        mac = netifaces.ifaddresses(card)[TCP_PROTOCOL][0]["addr"]
        return mac
