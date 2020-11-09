# coding=utf-8
import logging
import threading
from os.path import getsize
import math

logger = logging.getLogger(__name__)


class ClientSession(object):

    def __init__(self, client, client_key=None, server_key=None, mac_socket=None, src_mac=None, dest_mac=None,
                 session=None):
        self.client = client
        self.client_key = client_key
        self.server_key = server_key
        self.mac_socket = mac_socket
        self.src_mac = src_mac
        self.dest_mac = dest_mac
        self.receive_condition = threading.Condition()
        self.receive_data = None
        self.default_interval_length = 900000
        self.default_packet_length = 300
        self.file_path = None

    def __enter__(self):
        """
        打开session，认证过程
        """
        pass

    def __exit__(self):
        """
        退出session
        """
        self.mac_socket.close_session()
        self.client.close_session(self)

    def set_receive_data(self, data):
        """
        设置接收数据变量
        """
        with self.receive_condition:
            self.receive_data = data[2]
            if self.receive_data.ptype == 1:
                pass
            elif self.receive_data.ptype == 2 and self.receive_data.sequence:
                pass
            elif self.receive_data.ptype == 2 and self.receive_data.sequence is None:
                self.authentication(self.receive_data)
            elif self.receive_data.ptype == 3:
                self.authentication(self.receive_data)
            elif self.receive_data.ptype == 255:
                self.close_conn()
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
                                      data=f.read(self.default_packet_length), client_key=self.client_key)
        f.close()
        return "ok"

    def authentication(self, data):

        self.server_key = self.receive_data.server_key
        self.mac_socket.send_func_packet(self.dest_mac, ptype=3, server_key=self.server_key, data="", client_key=self.client_key)

        if data.data is None:
            return "ok"

    def init_conn(self):
        self.mac_socket.send_func_packet(dst_mac=self.dest_mac, ptype=0, session=self.client_key)
        """
        握手结束，开始认证
        """

    def close_conn(self):
        self.mac_socket.send_func_packet(dst_mac=self.dest_mac, ptype=255, session=self.client_key)