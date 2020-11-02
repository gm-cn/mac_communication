import logging


logger = logging.getLogger(__name__)


class MACSocket(object):

    def __init__(self):
        pass

    def receive_frame(self):
        """
        二层接收帧数据包Frame，接收之后返回ACK
        """
        pass

    def send_frame(self):
        """
        二层发送帧数据包Frame，记录发送的数据，并超时重试
        """
        pass

    def receive_data(self):
        """
        一个sequence中接收的数据，并排序重组，返回Packet
        """
        pass

    def send_data(self):
        """
        发送sequence数据Packet，并拆分为帧包，所有数据都收到ACK，才算发送完成
        """
        pass

    def open_session(self):
        """
        客户端发送开启一个session
        """
        pass

    def ack_open_session(self):
        """服务端确认开启session"""
        pass

    def close_session(self):
        """
        客户端发送关闭session
        """

    def ack_close_session(self):
        """服务端确认关闭session"""
        pass
