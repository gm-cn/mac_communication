# coding=utf-8
import logging


logger = logging.getLogger(__name__)


class PacketType(object):
    OpenSession = 0
    Data = 1
    Ack = 2
    Control = 3
    EndSession = 255


class Frame(object):
    """
    二层收发帧数据
    """

    def __init__(self, src_mac=None, dest_mac=None, client_key=None, server_key=None, ptype=None, sequence=None,
                 count=None, offset=None, vlan=None, length=None, data=None):
        self.src_mac = src_mac
        self.dest_mac = dest_mac
        self.client_key = client_key
        self.server_key = server_key
        self.ptype = ptype
        self.sequence = sequence
        self.count = count
        self.offset = offset
        self.vlan = vlan
        self.length = length
        self.data = data


class PacketFrames(object):
    """

    """
    def __init__(self, src_mac=None, dest_mac=None, client_key=None, server_key=None, ptype=None, sequence=None,
                 vlan=None, count=None):
        self.src_mac = src_mac
        self.dest_mac = dest_mac
        self.client_key = client_key
        self.server_key = server_key
        self.ptype = ptype
        self.sequence = sequence
        self.count = count
        self.vlan = vlan
        self.frames = {}
        self.receive_count = 0

    def add_frame(self, frame):
        if frame.offset not in self.frames:
            self.receive_count += 1
        self.frames[frame.offset] = frame.data

    def has_receive_all(self):
        if self.receive_count == self.count:
            return True
        return False

    def packet_data(self):
        data = ''
        for i in range(self.count):
            data += self.frames[i]
        return data


class Packet(object):
    """
    sequence收发数据包结构
    """

    def __init__(self, src_mac=None, dest_mac=None, client_key=None, server_key=None, ptype=None, sequence=None,
                 vlan=None, data=None):
        self.src_mac = src_mac
        self.dest_mac = dest_mac
        self.client_key = client_key
        self.server_key = server_key
        self.ptype = ptype
        self.sequence = sequence
        self.vlan = vlan
        self.data = data

    def is_new_session(self):
        if self.ptype == PacketType.OpenSession:
            return True
        return False


class ControlPacket(object):
    """
    控制包结构
    """

    def __init__(self, ctype=None, data=None):
        self.ctype = ctype
        self.data = data
