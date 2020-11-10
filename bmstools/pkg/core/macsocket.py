# coding=utf-8
import socket
import struct
import binascii
from functools import reduce
import math

from .packet import Frame, PacketType, Packet, PacketFrames

import logging

ETH_P_BMS = 0x7fff
ETH_P_VLAN = 0x8100
BuffSize = 65536

logger = logging.getLogger(__name__)


class MACSocket(object):

    def __init__(self):
        self.net_card = self.get_send_net_card()
        self.receive_socket = socket.socket(socket.PF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_BMS))
        self.send_socket = socket.socket(socket.PF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_BMS))
        self.send_socket.bind((self.net_card, socket.htons(ETH_P_BMS)))
        self.ETH_P_BMS_BY = self.format_mac_bytes(self.i2b_hex(ETH_P_BMS))
        self.default_interval_length = 900000
        self.default_packet_length = 300
        self.packet_list = {"client_key": {"num": None}}
        self.receive_frame_caches = {}
        self.send_frame_caches = {}

    @classmethod
    def get_send_net_card(cls):
        return "bond0"

    @classmethod
    def frame_cache_key(cls, frame):
        return '%s:%s:%s' % (frame.sequence, frame.count, frame.offset)

    def receive_frame(self):
        """
        二层接收帧数据包Frame，接收之后返回ACK
        """
        packet, packet_info = self.receive_socket.recvfrom(BuffSize)
        logger.info("receive packet: %s", packet)
        eth_header = packet[0:14]
        src_mac, dst_mac, eth_type = struct.unpack("!6s6s2s", eth_header)
        if eth_type != '\x7f\xff':
            logger.error("receive eth type %s is not bms type" % (eth_type, ))
            return
        ver, ptype, client_session_key = struct.unpack('!BBH', packet[14: 18])
        frame = Frame(src_mac=src_mac,
                      dest_mac=dst_mac,
                      client_key=client_session_key,
                      ptype=ptype)
        # if ptype in (PacketType.Ack, PacketType.Data, PacketType.Control):
        server_session_key, sequence, count, offset, length = struct.unpack('!HIHHH', packet[18: 30])
        frame.server_key = server_session_key
        frame.sequence = sequence
        frame.count = count
        frame.offset = offset
        frame.length = length
        if ptype == PacketType.Data:
            frame.data = packet[30: 30 + frame.length]

        # 返回Ack确认包
        ack_frame = Frame(src_mac=frame.dest_mac,
                          dest_mac=frame.src_mac,
                          client_key=frame.client_key,
                          server_key=frame.server_key,
                          ptype=PacketType.Ack,
                          sequence=frame.sequence,
                          count=frame.count,
                          offset=frame.offset)
        self.send_frame(ack_frame)
        return frame

    def receive_data(self):
        """
        一个sequence中接收的数据，并排序重组，返回Packet
        """
        while True:
            frame = self.receive_frame()
            logger.info("receive frame ptype: %s" % (frame.ptype,))
            if frame.ptype == PacketType.OpenSession:
                # 开启一个新的session，直接返回packet包
                packet = Packet(src_mac=frame.src_mac,
                                dest_mac=frame.dest_mac,
                                client_key=frame.client_key,
                                ptype=frame.ptype)
                return packet
            if frame.ptype == PacketType.Ack:
                # 处理Ack，删除cache中的frame
                if frame.client_key in self.send_frame_caches:
                    cache_key = self.frame_cache_key(frame)
                    if cache_key in self.send_frame_caches.get(frame.client_key):
                        self.send_frame_caches[frame.client_key].pop(cache_key)
            elif frame.ptype in (PacketType.Data, PacketType.Control):
                # 数据包或控制包，组合count所有的offset之后返回packet包
                if frame.server_key not in self.receive_frame_caches:
                    packet_frames = PacketFrames(src_mac=frame.src_mac,
                                                 dest_mac=frame.dest_mac,
                                                 client_key=frame.client_key,
                                                 server_key=frame.server_key,
                                                 ptype=frame.ptype,
                                                 sequence=frame.sequence,
                                                 count=frame.count)
                    # 根据server_key添加缓存组合offset
                    self.receive_frame_caches[frame.server_key] = packet_frames
                packet_frames = self.receive_frame_caches.get(frame.server_key)
                packet_frames.add_frame(frame)
                if packet_frames.has_receive_all():
                    data = packet_frames.packet_data()
                    packet = Packet(src_mac=frame.src_mac,
                                    dest_mac=frame.dest_mac,
                                    client_key=frame.client_key,
                                    server_key=frame.server_key,
                                    ptype=frame.ptype,
                                    sequence=frame.sequence,
                                    data=data)
                    # 删除offset缓存
                    self.receive_frame_caches.pop(frame.server_key)
                    return packet

    def send_frame(self, frame):
        """
        二层发送帧数据包Frame，记录发送的数据，并超时重试
        """
        version = 1
        send_frame = struct.pack("!6s6s2s",
                                 frame.dest_mac,
                                 frame.src_mac,
                                 self.ETH_P_BMS_BY)
        send_frame += struct.pack("!BBHH",
                                  version,
                                  int(frame.ptype),
                                  int(frame.client_key),
                                  int(frame.server_key))
        send_frame += struct.pack("!IHH",
                                  frame.sequence,
                                  frame.count,
                                  frame.offset)
        if frame.data:
            send_frame += struct.pack("!H", frame.length)
            send_frame += frame.data
        else:
            send_frame += struct.pack("!H", 0)
        self.send_socket.send(send_frame)
        if frame.ptype != PacketType.Ack:
            if frame.client_key not in self.send_frame_caches:
                self.send_frame_caches[frame.client_key] = {}
            send_frame_caches = self.send_frame_caches.get(frame.client_key)
            send_frame_caches['%s:%s:%s' % (frame.sequence, frame.count, frame.offset)] = frame

    def send_data(self, packet):
        """
        发送sequence数据Packet，并拆分为帧包，所有数据都收到ACK，才算发送完成
        """
        if packet.ptype == PacketType.OpenSession:
            frame = Frame(src_mac=packet.src_mac,
                          dest_mac=packet.dest_mac,
                          client_key=packet.client_key,
                          server_key=packet.server_key,
                          ptype=packet.ptype,
                          sequence=0,
                          count=0,
                          offset=0,
                          length=0)
            self.send_frame(frame)
        elif packet.ptype in (PacketType.Data, PacketType.Control):
            count, offset = 0, 0
            if packet.data:
                count = math.ceil(len(packet.data) / self.default_packet_length)
            if count > 0:
                for i in range(count):
                    frame_data = packet.data[i * self.default_packet_length: (i + 1) * self.default_packet_length]
                    frame = Frame(src_mac=packet.src_mac,
                                  dest_mac=packet.dest_mac,
                                  client_key=packet.client_key,
                                  server_key=packet.server_key,
                                  ptype=packet.ptype,
                                  sequence=packet.sequence,
                                  count=count,
                                  offset=i,
                                  length=len(frame_data),
                                  data=frame_data)
                    self.send_frame(frame)
            else:
                frame = Frame(src_mac=packet.src_mac,
                              dest_mac=packet.dest_mac,
                              client_key=packet.client_key,
                              server_key=packet.server_key,
                              ptype=packet.ptype,
                              sequence=packet.sequence,
                              count=count,
                              offset=offset,
                              length=0,
                              data='')
                self.send_frame(frame)

    @classmethod
    def format_mac(cls, mac_address):
        return mac_address.replace(":", "")

    @classmethod
    def format_mac_bytes(cls, msg):
        return reduce(lambda x, y: x + y, [binascii.unhexlify(msg[i:i + 2]) for i in range(0, len(msg), 2)])

    @classmethod
    def i2b_hex(cls, protocol):
        b_protocol = hex(int(protocol))[2:]
        return b_protocol if len(b_protocol) % 2 == 0 else '0{0}'.format(b_protocol).encode('utf8')


