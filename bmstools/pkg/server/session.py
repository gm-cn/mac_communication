import logging


logger = logging.getLogger(__name__)


class ServerSession(object):

    def __init__(self, server, client_key=None, server_key=None, mac_socket=None, src_mac=None, dest_mac=None):
        self.server = server
        self.client_key = client_key
        self.server_key = server_key
        self.mac_socket = mac_socket
        self.src_mac = src_mac
        self.dest_mac = dest_mac

    def response(self, data):
        """
        服务端对客户端响应
        """
        self.mac_socket.send_data(data)

    def handle_data(self, packet):
        logger.info(packet)
        self.response("ok")
