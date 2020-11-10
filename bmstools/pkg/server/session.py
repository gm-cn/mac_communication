# coding=utf-8
import logging

from bmstools.pkg.core.packet import Packet, PacketType

logger = logging.getLogger(__name__)


class ServerSession(object):

    def __init__(self, server, mac_socket=None, client_key=None, server_key=None, src_mac=None, dest_mac=None):
        self.server = server
        self.mac_socket = mac_socket
        self.client_key = client_key
        self.server_key = server_key
        self.src_mac = src_mac
        self.dest_mac = dest_mac
        self.sequence = 0

        # self.receive_condition = threading.Condition()
        # self.receive_data = None
        # self.default_interval_length = 900000
        # self.default_packet_length = 300
        # self.file_path = "/home/ddd"

        self.ctype = -1
        self.save_file = ""

    def response(self, ptype, data=''):
        """
        服务端对客户端响应
        """
        packet = Packet(src_mac=self.src_mac,
                        dest_mac=self.dest_mac,
                        client_key=self.client_key,
                        server_key=self.server_key,
                        ptype=ptype,
                        sequence=self.sequence,
                        data=data)
        self.mac_socket.send_data(packet)
        self.sequence += 1

    def ack_open_session(self):
        logger.info("send ack open session")
        self.response(PacketType.OpenSession)

    def handle_data(self, packet):
        """
        接收到数据处理
        """
        # self.set_receive_data(packet)
        # logger.info(packet.data)
        if packet.ptype == PacketType.Control:
            pass
        self.response(PacketType.Data, "hello")

    # def set_receive_data(self, data):
    #     """
    #     设置接收数据变量
    #     """
    #     with self.receive_condition:
    #         self.receive_data = data[2]
    #         if self.receive_data.ptype == 1:
    #             self.save_file(self.receive_data)
    #         elif self.receive_data.ptype == 2 and self.receive_data.sequence:
    #             pass
    #         elif self.receive_data.ptype == 2 and self.receive_data.sequence is None:
    #             self.init_conn()
    #         elif data.ptype == 3:
    #             """
    #             认证过程
    #             """
    #             self.authentication(data)
    #         elif self.receive_data.ptype == 0:
    #             """
    #             创建seskey返回
    #             """
    #             self.dst_Mac = data[1].decode("utf-8")
    #             self.server_key = ""
    #             self.client_key = self.receive_data.client_key
    #             self.mac_socket.send_func_packet(self.dest_mac, ptype=2, server_key=self.server_key,
    #                                              client_key=self.client_key)
    #         elif self.receive_data.ptype == 255:
    #             data = None
    #             self.mac_socket.send_func_packet(self.dest_mac, ptype=255, server_key=self.server_key,
    #                                              client_key=self.client_key, data=data)
    #             self.close_conn()
    #         self.receive_condition.notify()
    #
    # def receive_data(self):
    #     """
    #     从macsocket获取接收数据或返回数据
    #     """
    #     self.receive_data = None
    #     with self.receive_condition:
    #         if not self.receive_data:
    #             self.receive_condition.wait()
    #     return self.receive_data
    #
    # def send_file(self, file_path):
    #     file_length = getsize(file_path)
    #     file_sequence = math.ceil(file_length / self.default_interval_length)
    #     f = open(file_path, "rb")
    #     for i in range(file_sequence):
    #         self.mac_socket.send_data(dst_mac=self.dest_mac, sequence=i, server_key=self.server_key,
    #                                   data=f.read(self.default_packet_length), )
    #     f.close()
    #
    # def authentication(self, data):
    #     """
    #     认证过程
    #     self.dst_Mac = data[1].decode("utf-8")
    #     self.server_key = self.receive_data.server_key
    #     self.mac_socket.send_func_packet(self.dest_mac, ptype=3, server_key=self.server_key, data="",
    #     client_key=self.client_key)
    #     """
    #     pass
    #
    # def init_conn(self):
    #     self.mac_socket.send_func_packet(dst_mac=self.dest_mac, ptype=0, session=self.client_key)
    #     """
    #     握手结束，开始认证
    #     """
    #     self.authentication(data="")
    #
    # def close_conn(self):
    #     self.mac_socket.send_func_packet(dst_mac=self.dest_mac, ptype=255, session=self.client_key)
    #
    # def save_file(self, data):
    #     with open(self.file_path, "ab") as f:
    #         f.write(data)
