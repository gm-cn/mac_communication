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
        self.mac_socket = MACSocket()
        self.mac_socket.net_card = "bond0"
        self.mac_socket.src_mac = self.mac_socket.get_mac(self.mac_socket.net_card)
        self.sessions = {}
        self.key_lock = threading.Lock()
        super().__init__(*args, **kwargs)

    def run(self):
        """
        从二层网卡接收数据，转发数据到对应已创建的session
        """
        while True:
            try:
                packet = self.mac_socket.receive_data()
                if packet.client_key:
                    if packet.client_key in self.sessions:
                        client_session = self.sessions.get(packet.client_key)
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
            for i in range(65536):
                if i not in self.sessions:
                    return i

    def new_session(self, dest_mac, vlan):
        """
        客户端创建一个新的session
        """
        client_key = self.get_new_client_key()
        cs = ClientSession(self, client_key=client_key, mac_socket=self.mac_socket, dest_mac=dest_mac, vlan=vlan)
        self.sessions[client_key] = cs

    def close_session(self, session):
        """
        关闭session
        """

        self.sessions.pop(session.client_key)


if __name__ == "__main__":
    client = get_client()
    with client.new_session(dest_mac="", vlan="") as session:
        session.init_conn()
        session.send_file("/tmp/aaa")
        session.close_conn()
        resp = session.exec_cmd("ls /root")