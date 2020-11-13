# coding=utf-8
import os
import logging
import threading
from time import sleep

from .session import ServerSession
from ..core.macsocket import MACSocket

logger = logging.getLogger(__name__)

_bms_tools_server = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def get_server():
    """
    全局唯一server实例
    """
    global _bms_tools_server
    if not _bms_tools_server:
        _bms_tools_server = Server()
    return _bms_tools_server


class Server(object):

    def __init__(self):
        self.mac_socket = MACSocket()
        self.sessions = {}
        self.key_lock = threading.Lock()
        with open(os.path.join(BASE_DIR, "public.pem")) as f:
            self.public_key = f.read()

    def run(self):
        """
        从二层网卡接收数据，转发数据到对应已创建的session
        """
        logger.info("server start receive data")
        while True:
            try:
                packet = self.mac_socket.receive_data()
                if packet.is_new_session():
                    self.new_session(packet.src_key, packet.dest_mac, packet.src_mac, packet.vlan)
                else:
                    if packet.dest_key in self.sessions:
                        server_session = self.sessions.get(packet.dest_key)
                        server_session.handle_data(packet)
                    else:
                        logger.error("server not found session %s" % packet.src_key)
            except Exception as exc:
                logger.error("receive data error: %s" % exc, exc_info=True)
                sleep(3)

    def get_new_server_key(self):
        with self.key_lock:
            for i in range(1, 65536):
                if i not in self.sessions:
                    return i

    def new_session(self, dest_key, src_mac, dest_mac, vlan):
        """
        服务端创建一个新的session
        """
        src_key = self.get_new_server_key()
        logger.info("start new session, src_key: %s, dest_key: %s, src_mac: %s, dest_mac: %s, vlan: %s" % (
            src_key,
            dest_key,
            src_mac,
            dest_mac,
            vlan))
        ss = ServerSession(self,
                           mac_socket=self.mac_socket,
                           src_key=src_key,
                           dest_key=dest_key,
                           src_mac=src_mac,
                           dest_mac=dest_mac,
                           vlan=vlan)
        ss.ack_open_session()
        self.sessions[src_key] = ss

    def close_session(self, session):
        """
        关闭session
        """
        self.mac_socket.clean_session(session.src_key)
        self.sessions.pop(session.src_key)
