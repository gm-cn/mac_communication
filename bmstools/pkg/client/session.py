import logging
import threading


logger = logging.getLogger(__name__)


class ClientSession(object):

    def __init__(self, client, client_key=None, server_key=None, mac_socket=None, src_mac=None, dest_mac=None):
        self.client = client
        self.client_key = client_key
        self.server_key = server_key
        self.mac_socket = mac_socket
        self.src_mac = src_mac
        self.dest_mac = dest_mac
        self.receive_condition = threading.Condition()
        self.receive_data = None

    def __enter__(self):
        """
        打开session
        """
        packet = self.mac_socket.open_session()
        self.server_key = packet.server_key

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
            self.receive_data = data
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

    def request(self, data):
        """
        对服务端发送请求
        """
        self.mac_socket.send_data(data)
        rd = self.receive_data()
        return rd

    def exec_cmd(self, cmd):
        resp = self.request(cmd)
        logger.info(resp)
