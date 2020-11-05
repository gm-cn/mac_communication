import logging


logger = logging.getLogger(__name__)


class Frame(object):
    """
    二层收发帧数据
    """

    def __init__(self, src_mac=None, dest_mac=None, client_key=None, server_key=None, ptype=None, sequence=None,
                 count=None, offset=None, data=None, session=None):
        self.src_mac = src_mac
        self.dest_mac = dest_mac
        self.client_key = client_key
        self.server_key = server_key
        self.ptype = ptype
        self.sequence = sequence
        self.count = count
        self.offset = offset
        self.data = data


class Packet(object):
    """
    sequence收发数据包结构
    """

    def __init__(self, src_mac=None, dest_mac=None, client_key=None, server_key=None, ptype=None, sequence=None,
                 data=None, session=None):
        self.src_mac = src_mac
        self.dest_mac = dest_mac
        self.client_key = client_key
        self.server_key = server_key
        self.ptype = ptype
        self.sequence = sequence
        self.data = data
        self.session = session

    def is_new_session(self):
        if self.ptype == 1:
            return True
        return False


class ControlPacket(object):
    """
    控制包结构
    """

    def __init__(self, ctype=None, data=None):
        self.ctype = ctype
        self.data = data
