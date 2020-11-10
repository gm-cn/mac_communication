# coding=utf-8
import logging
import threading
from time import sleep

from .session import ServerSession
from ..core.macsocket import MACSocket

logger = logging.getLogger(__name__)


_bms_tools_server = None


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

    def run(self):
        """
        从二层网卡接收数据，转发数据到对应已创建的session
        """
        while True:
            try:
                packet = self.mac_socket.receive_data()
                if packet.is_new_session():
                    self.new_session(packet.client_key, packet.dest_mac, packet.src_mac)
                else:
                    if packet.server_key in self.sessions:
                        server_session = self.sessions.get(packet.server_key)
                        server_session.handle_data(packet)
                    else:
                        logger.error("server not found session %s" % packet.client_key)
            except Exception as exc:
                logger.error("receive data error: %s" % exc, exc_info=True)
                sleep(3)

    def get_new_server_key(self):
        with self.key_lock:
            for i in range(1, 65536):
                if i not in self.sessions:
                    return i

    def new_session(self, client_key, src_mac, dest_mac):
        """
        客户端创建一个新的session
        """
        server_key = self.get_new_server_key()
        logger.info("start new session, client_key: %s, server_key: %s, src_mac: %s, dest_mac: %s" % (client_key,
                                                                                                      server_key,
                                                                                                      src_mac,
                                                                                                      dest_mac))
        # session_state = SessionState(client_key=client_key, server_key=server_key, src_mac=src_mac, dest_mac=dest_mac)
        ss = ServerSession(self, mac_socket=self.mac_socket, client_key=client_key, server_key=server_key,
                           src_mac=src_mac, dest_mac=dest_mac)
        ss.ack_open_session()
        self.sessions[server_key] = ss

    def close_session(self, session):
        """
        关闭session
        """
        self.sessions.pop(session.client_key)


if __name__ == '__main__':
    server = get_server()
    server.run()
