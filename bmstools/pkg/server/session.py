import logging
import threading

from functools import reduce
from queue import Queue
import time
from os.path import getsize
import math
import base64
import copy

from ..core.packet import Frame
from ..core.packet import ControlPacket

logger = logging.getLogger(__name__)


class ServerSession(object):

    def __init__(self, server, client_key=None, server_key=None, mac_socket=None):
        self.server = server
        self.mac_socket = mac_socket
        self.mac_socket.net_card = None
        self.src_mac = None
        self.dest_mac = None
        self.vlan = None
        self.client_key = None
        self.server_key = server_key
        self.send_socket = None

        self.receive_condition = threading.Condition()
        self.receive_data = None
        self.default_interval_length = 900000
        self.default_packet_length = 300
        self.file_path = "/home/ddd"

    def response(self, data):
        """
        服务端对客户端响应
        """
        self.mac_socket.send_data(data)

    def set_receive_data(self, data):
        """
        设置接收数据变量
        """
        with self.receive_condition:
            self.receive_data = data[2]
            if self.receive_data["ptype"] == 1:
                self.save_file(self.receive_data["data"])
                print(self.dest_mac, self.server_key, self.client_key, data, self.vlan)
            elif self.receive_data["ptype"] == 2 and self.receive_data["sequence"]:
                pass
            elif self.receive_data["ptype"] == 2 and self.receive_data["sequence"] is None:
                self.init_conn()
            elif self.receive_data["ptype"] == 3:
                """
                认证过程
                """
                self.authentication(data)
            elif self.receive_data["ptype"] == 0:
                """
                创建seskey返回
                """
                self.dest_mac = data[1].decode("utf-8")
                self.src_mac = data[0].decode("utf-8")
                self.vlan = self.receive_data["vlan"]
                self.mac_socket.net_card = self.mac_socket.get_net(self.src_mac)[0]
                self.mac_socket.src_mac = self.src_mac
                self.server_key = ""
                self.client_key = self.receive_data["client_key"]
                self.send_socket = self.mac_socket.set_send_socket()
                self.mac_socket.send_func_packet(self.dest_mac, ptype=2, server_key=self.server_key,
                                                 client_key=self.client_key, vlan=self.vlan, raw_socket=self.send_socket)
                print(self.dest_mac, self.server_key, self.client_key, data, self.vlan)
            elif self.receive_data["ptype"] == 255:
                print(self.dest_mac, self.server_key, self.client_key, data, self.vlan)
                self.mac_socket.send_func_packet(self.dest_mac, ptype=255, server_key=self.server_key, client_key=self.client_key,
                                                 data=data, vlan=self.vlan, raw_socket=self.send_socket)
                self.close_conn()
                data = None
            self.receive_condition.notify()

    def handle_data(self, packet):
        """
        接收到数据处理
        """
        self.set_receive_data(packet)

    def receive_data(self):
        """
        从macsocket获取接收数据或返回数据
        """
        self.receive_data = None
        with self.receive_condition:
            if not self.receive_data:
                self.receive_condition.wait()
        return self.receive_data

    def request(self):
        """
        对服务端发送请求
        """
        pass

    def exec_cmd(self, cmd):
        resp = self.request()
        logger.info(resp)

    def send_file(self, file_path):
        file_length = getsize(file_path)
        file_sequence = math.ceil(file_length / self.default_interval_length)
        f = open(file_path, "rb")
        for i in range(file_sequence):
            self.mac_socket.send_data(dst_mac=self.dest_mac, sequence=i, server_key=self.server_key,
                                      data=f.read(self.default_packet_length), vlan=self.vlan, raw_socket=self.send_socket)
        f.close()

    def authentication(self, data):
        """
        认证过程
        self.dst_Mac = data[1].decode("utf-8")
        self.server_key = self.receive_data.server_key
        self.mac_socket.send_func_packet(self.dest_mac, ptype=3, server_key=self.server_key, data="", client_key=self.client_key)
        """
        pass

    def init_conn(self):
        self.mac_socket.send_func_packet(dst_mac=self.dest_mac, ptype=0, session=self.client_key, vlan=self.vlan,
                                         raw_socket=self.send_socket)
        """
        握手结束，开始认证
        """
        self.authentication(data="")

    def close_conn(self):
        self.mac_socket.send_func_packet(dst_mac=self.dest_mac, ptype=255, client_key=self.client_key, vlan=self.vlan,
                                         raw_socket=self.send_socket)

    def save_file(self, data):
        with open(self.file_path, "ab") as f:
            f.write(data)