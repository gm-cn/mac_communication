# coding=utf-8
import threading
import logging
from time import sleep

from ..core.macsocket import MACSocket
from .session import ClientSession

logger = logging.getLogger(__name__)


_bms_tools_client = None


def get_client():
    """
    全局唯一client实例
    """
    global _bms_tools_client
    if not _bms_tools_client:
        _bms_tools_client = Client()
    return _bms_tools_client


class Client(threading.Thread):

    def __init__(self, *args, **kwargs):
        self.src_mac = self.get_src_mac()
        self.mac_socket = MACSocket()
        self.sessions = {}
        self.key_lock = threading.Lock()
        super(Client, self).__init__(*args, **kwargs)

    @classmethod
    def get_src_mac(cls):
        return ""

    def run(self):
        """
        从二层网卡接收数据，转发数据到对应已创建的session
        """
        logger.info("client start receive data")
        while True:
            try:
                packet = self.mac_socket.receive_data()
                if packet.dest_key:
                    if packet.dest_key in self.sessions:
                        client_session = self.sessions.get(packet.dest_key)
                        client_session.handle_data(packet)
                    else:
                        logger.error("client not found session %s" % packet.client_key)
                else:
                    logger.error("receive data not found client key")
            except Exception as exc:
                logger.error("receive data error: %s" % exc, exc_info=True)
                sleep(3)

    def get_new_client_key(self):
        with self.key_lock:
            for i in range(1, 65536):
                if i not in self.sessions:
                    return i

    def new_session(self, dest_mac, vlan, src_mac=None):
        """
        客户端创建一个新的session
        """
        src_key = self.get_new_client_key()
        if not src_mac:
            src_mac = self.src_mac
        cs = ClientSession(self,
                           src_key=src_key,
                           mac_socket=self.mac_socket,
                           src_mac=src_mac,
                           dest_mac=dest_mac,
                           vlan=vlan)
        self.sessions[src_key] = cs
        return cs

    def close_session(self, session):
        """
        关闭session
        """
        self.mac_socket.clean_session(session.src_key)
        self.sessions.pop(session.src_key)
