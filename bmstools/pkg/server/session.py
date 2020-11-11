# coding=utf-8
import logging

from bmstools.pkg.core.response import Response, Code
from bmstools.utils import shell
from ..core.packet import Packet, PacketType, ControlType, ControlPacket

logger = logging.getLogger(__name__)


class ServerSession(object):

    def __init__(self, server, mac_socket=None, src_key=None, dest_key=None, src_mac=None, dest_mac=None, vlan=None):
        self.server = server
        self.mac_socket = mac_socket
        self.src_key = src_key
        self.dest_key = dest_key
        self.src_mac = src_mac
        self.dest_mac = dest_mac
        self.sequence = 0
        self.vlan = vlan

        # self.receive_condition = threading.Condition()
        # self.receive_data = None
        # self.default_interval_length = 900000
        # self.default_packet_length = 300
        # self.file_path = "/home/ddd"

        self.ctype = ControlType.Noop
        self.save_file_path = ""

    def response(self, ptype, data=''):
        """
        服务端对客户端响应
        """
        packet = Packet(src_mac=self.src_mac,
                        dest_mac=self.dest_mac,
                        src_key=self.src_key,
                        dest_key=self.dest_key,
                        ptype=ptype,
                        sequence=self.sequence,
                        vlan=self.vlan,
                        data=data)
        self.mac_socket.send_data(packet)
        self.sequence += 1

    def ack_open_session(self):
        logger.info("send ack open session")
        self.response(PacketType.OpenSession)

    def ack_end_session(self):
        logger.info("send ack end session")
        self.response(PacketType.EndSession)

    def _handle_data(self, packet):
        if packet.ptype == PacketType.Control:
            control = ControlPacket.unpack(packet.data)
            self.ctype = control.ctype
            if self.ctype == ControlType.File:
                # 传输文件，data为文件路径名
                self.save_file_path = control.data
                if not self.save_file_path:
                    return Response(Code.ParameterError, "Save file path is empty")
                return Response(Code.Success)
            elif self.ctype == ControlType.Exec:
                # 执行命令
                return self.exec_cmd(control.data)
            elif self.ctype == ControlType.Auth:
                # session认证
                pass
        elif packet.ptype == PacketType.Data:
            # 数据包，当前只有传输文件时会使用
            if self.ctype == ControlType.File:
                if self.save_file_path:
                    return self.save_file(packet.data)
                else:
                    return Response(Code.LogicError, "Session save file path is empty")
            else:
                Response(Code.LogicError, "Session receive data but is not file")
        elif packet.ptype == PacketType.EndSession:
            self.ack_end_session()
            self.server.close_session(self)
        else:
            Response(Code.LogicError, "Session can not process packet type %s" % (packet.ptype,))

    def handle_data(self, packet):
        """
        接收到数据处理
        """
        if packet.ptype == PacketType.EndSession:
            logger.info("start end session %s" % self.src_key)
            self.ack_end_session()
            self.server.close_session(self)
            logger.info("end session %s success" % self.src_key)
        else:
            logger.info("receive packet data: %s" % (packet.data,))
            resp = self._handle_data(packet)
            self.response(PacketType.Data, resp.pack())

    def exec_cmd(self, cmd):
        s = shell.call(cmd)
        resp = {
            "code": s.return_code,
            "stdout": s.stdout,
            "stderr": s.stderr
        }
        return Response(Code.Success, data=resp)

    def save_file(self, data):
        logger.info("save data: %s" % data)
        return Response(Code.Success, msg="save file %s success" % (self.save_file_path,))

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
    #             self.dest_key = ""
    #             self.src_key = self.receive_data.src_key
    #             self.mac_socket.send_func_packet(self.dest_mac, ptype=2, dest_key=self.dest_key,
    #                                              src_key=self.src_key)
    #         elif self.receive_data.ptype == 255:
    #             data = None
    #             self.mac_socket.send_func_packet(self.dest_mac, ptype=255, dest_key=self.dest_key,
    #                                              src_key=self.src_key, data=data)
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
    #         self.mac_socket.send_data(dst_mac=self.dest_mac, sequence=i, dest_key=self.dest_key,
    #                                   data=f.read(self.default_packet_length), )
    #     f.close()
    #
    # def authentication(self, data):
    #     """
    #     认证过程
    #     self.dst_Mac = data[1].decode("utf-8")
    #     self.dest_key = self.receive_data.dest_key
    #     self.mac_socket.send_func_packet(self.dest_mac, ptype=3, dest_key=self.dest_key, data="",
    #     src_key=self.src_key)
    #     """
    #     pass
    #
    # def init_conn(self):
    #     self.mac_socket.send_func_packet(dst_mac=self.dest_mac, ptype=0, session=self.src_key)
    #     """
    #     握手结束，开始认证
    #     """
    #     self.authentication(data="")
    #
    # def close_conn(self):
    #     self.mac_socket.send_func_packet(dst_mac=self.dest_mac, ptype=255, session=self.src_key)
    #
    # def save_file(self, data):
    #     with open(self.file_path, "ab") as f:
    #         f.write(data)
