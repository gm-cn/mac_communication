import threading
import logging
from time import sleep

from ..core.macsocket import MACSocket
from .session import ClientSession

import os
import logging
import logging.config

LOG_SETTINGS = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'detailed',
            'stream': 'ext://sys.stdout',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'filename': '/var/log/cdsstack/baremetal-api.log',
            'mode': 'a',
            'maxBytes': 10485760,
            'backupCount': 5,
        },

    },
    'formatters': {
        'detailed': {
            'format': '%(asctime)s %(levelname)s %(process)d \
%(name)s.%(lineno)d %(message)s',
        },
        'email': {
            'format': 'Timestamp: %(asctime)s\nModule: %(module)s\n'
                      'Line: %(lineno)d\nMessage: %(message)s',
        },
    },
    'loggers': {
        'baremetal': {
            'level': 'DEBUG',
            'handlers': ['file', 'console']
        },
    }
}


def setup(path='/var/log/cdsstack'):
    if not os.path.exists(path):
        os.makedirs(path)
    logging.config.dictConfig(LOG_SETTINGS)
    logger = logging.getLogger('baremetal')
    return logger


logger = setup()


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
            print("------------")
            try:
                print("***************")
                packet = self.mac_socket.receive_data()
                local_mac, src_mac, data = packet[0], packet[1], packet[2]
                if data["client_key"]:
                    if data["client_key"] in self.sessions:
                        client_session = self.sessions.get(data["client_key"])
                        client_session.handle_data(packet)
                    else:
                        logger.error("client not found session %s" % data["client_key"])
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
        return cs

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