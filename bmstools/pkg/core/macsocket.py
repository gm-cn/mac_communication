# coding=utf-8
import logging
import socket
import struct
import binascii
from functools import reduce

from .packet import Frame, PacketType, Packet, PacketFrames

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
        self.ETH_P_VLAN_BY = self.format_mac_bytes(self.i2b_hex(ETH_P_VLAN))
        # self.default_interval_length = 900000
        self.max_frame_length = 300
        # self.packet_list = {"src_key": {"num": None}}
        self.receive_frame_caches = {}
        self.send_frame_caches = {}

    def set_send_socket(self):
        raw_socket = socket.socket(socket.PF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_BMS))
        raw_socket.bind((self.net_card, socket.htons(ETH_P_BMS)))
        return raw_socket

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
        # logger.info("receive packet: %s", packet)
        eth_header = packet[0:14]
        dst_mac, src_mac, eth_type = struct.unpack("!6s6s2s", eth_header)
        if eth_type != '\x7f\xff':
            logger.error("receive eth type %s is not bms type" % (eth_type,))
            return
        ver, ptype, src_key = struct.unpack('!BBH', packet[14: 18])
        dest_key, sequence, count, offset, vlan, length = struct.unpack('!HIHHIH', packet[18: 34])
        frame = Frame(src_mac=src_mac,
                      dest_mac=dst_mac,
                      src_key=src_key,
                      ptype=ptype,
                      dest_key=dest_key,
                      sequence=sequence,
                      count=count,
                      offset=offset,
                      vlan=vlan,
                      length=length)
        if ptype in (PacketType.Data, PacketType.Control):
            frame.data = packet[34: 34 + frame.length]

        logger.info("receive frame, src_key: %s, dest_key: %s, ptype: %s, src_mac: %s, dest_mac: %s, sequence: %s \
count: %s, offset: %s, vlan: %s, length: %s, data: %s" % (frame.src_key,
                                                          frame.dest_key,
                                                          frame.ptype,
                                                          frame.src_mac,
                                                          frame.dest_mac,
                                                          frame.sequence,
                                                          frame.count,
                                                          frame.offset,
                                                          frame.vlan,
                                                          frame.length,
                                                          frame.data))
        if frame.ptype != PacketType.Ack:
            # 返回Ack确认包
            ack_frame = Frame(src_mac=frame.dest_mac,
                              dest_mac=frame.src_mac,
                              src_key=frame.dest_key,
                              dest_key=frame.src_key,
                              ptype=PacketType.Ack,
                              sequence=frame.sequence,
                              count=frame.count,
                              offset=frame.offset,
                              vlan=vlan)
            self.send_frame(ack_frame, self.send_socket)
        return frame

    def receive_data(self):
        """
        一个sequence中接收的数据，并排序重组，返回Packet
        """
        while True:
            frame = self.receive_frame()
            # logger.info("receive frame ptype: %s" % (frame.ptype,))
            if frame.ptype == PacketType.OpenSession:
                # 开启一个新的session，直接返回packet包
                packet = Packet(src_mac=frame.src_mac,
                                dest_mac=frame.dest_mac,
                                src_key=frame.src_key,
                                dest_key=frame.dest_key,
                                ptype=frame.ptype,
                                vlan=frame.vlan)
                return packet
            if frame.ptype == PacketType.Ack:
                # 处理Ack，删除cache中的frame
                if frame.dest_key in self.send_frame_caches:
                    cache_key = self.frame_cache_key(frame)
                    if cache_key in self.send_frame_caches.get(frame.dest_key):
                        self.send_frame_caches[frame.dest_key].pop(cache_key)
            elif frame.ptype in (PacketType.Data, PacketType.Control):
                # 数据包或控制包，组合count所有的offset之后返回packet包
                if frame.dest_key not in self.receive_frame_caches:
                    packet_frames = PacketFrames(src_mac=frame.src_mac,
                                                 dest_mac=frame.dest_mac,
                                                 src_key=frame.src_key,
                                                 dest_key=frame.dest_key,
                                                 ptype=frame.ptype,
                                                 sequence=frame.sequence,
                                                 count=frame.count,
                                                 vlan=frame.vlan)
                    # 根据dest_key添加缓存组合offset
                    self.receive_frame_caches[frame.dest_key] = packet_frames
                packet_frames = self.receive_frame_caches.get(frame.dest_key)
                packet_frames.add_frame(frame)
                if packet_frames.has_receive_all():
                    # sequence已经接收到所有count
                    data = packet_frames.packet_data()
                    packet = Packet(src_mac=frame.src_mac,
                                    dest_mac=frame.dest_mac,
                                    src_key=frame.src_key,
                                    dest_key=frame.dest_key,
                                    ptype=frame.ptype,
                                    sequence=frame.sequence,
                                    vlan=frame.vlan,
                                    data=data)
                    # 删除offset缓存
                    self.receive_frame_caches.pop(frame.dest_key)
                    return packet

    def send_frame(self, frame, raw_socket):
        """
        二层发送帧数据包Frame，记录发送的数据，并超时重试
        """
        b_vlan = self.format_mac_bytes(self.i2b_hex(frame.vlan))
        version = 1
        send_frame = struct.pack("!6s6s2s2s2s",
                                 frame.dest_mac,
                                 frame.src_mac,
                                 self.ETH_P_VLAN_BY,
                                 b_vlan,
                                 self.ETH_P_BMS_BY)
        #a = struct.unpack("!6s6s2s2s2s", send_frame)
        #logger.info("send header : %s", send_frame)
        send_frame += struct.pack("!BBHH",
                                  version,
                                  int(frame.ptype),
                                  int(frame.src_key),
                                  int(frame.dest_key))
        send_frame += struct.pack("!IHH",
                                  frame.sequence,
                                  frame.count,
                                  frame.offset)
        send_frame += struct.pack("!I",
                                  frame.vlan)

        if frame.data:
            send_frame += struct.pack("!H", frame.length)
            send_frame += frame.data
        else:
            send_frame += struct.pack("!H", 0)
        logger.info("send frame, src_key: %s, dest_key: %s, ptype: %s, src_mac: %s, dest_mac: %s, sequence: %s \
count: %s, offset: %s, vlan: %s, length: %s, data: %s" % (frame.src_key,
                                                          frame.dest_key,
                                                          frame.ptype,
                                                          frame.src_mac,
                                                          frame.dest_mac,
                                                          frame.sequence,
                                                          frame.count,
                                                          frame.offset,
                                                          frame.vlan,
                                                          frame.length,
                                                          frame.data))
        raw_socket.send(send_frame)
        if frame.ptype != PacketType.Ack:
            if frame.src_key not in self.send_frame_caches:
                self.send_frame_caches[frame.src_key] = {}
            send_frame_caches = self.send_frame_caches.get(frame.src_key)
            cache_key = self.frame_cache_key(frame)
            send_frame_caches[cache_key] = frame

    def send_data(self, packet, raw_socket):
        """
        发送sequence数据Packet，并拆分为帧包，所有数据都收到ACK，才算发送完成
        """
        if packet.ptype == PacketType.OpenSession:
            frame = Frame(src_mac=packet.src_mac,
                          dest_mac=packet.dest_mac,
                          src_key=packet.src_key,
                          dest_key=packet.dest_key,
                          ptype=packet.ptype,
                          sequence=0,
                          vlan=packet.vlan,
                          count=1,
                          offset=0,
                          length=0)
            self.send_frame(frame, raw_socket)
        elif packet.ptype in (PacketType.Data, PacketType.Control):
            count, offset = 1, 0
            logger.info("send packet data: %s" % (packet.data,))
            if packet.data:
                count = int(len(packet.data) / self.max_frame_length)
                if len(packet.data) % self.max_frame_length:
                    count += 1
                for i in range(count):
                    if (i + 1) * self.max_frame_length > len(packet.data):
                        frame_data = packet.data[i * self.max_frame_length:]
                    else:
                        frame_data = packet.data[i * self.max_frame_length: (i + 1) * self.max_frame_length]
                    # if frame_data:
                    frame = Frame(src_mac=packet.src_mac,
                                  dest_mac=packet.dest_mac,
                                  src_key=packet.src_key,
                                  dest_key=packet.dest_key,
                                  ptype=packet.ptype,
                                  sequence=packet.sequence,
                                  vlan=packet.vlan,
                                  count=count,
                                  offset=i,
                                  length=len(frame_data),
                                  data=frame_data)
                    self.send_frame(frame, raw_socket)
            else:
                frame = Frame(src_mac=packet.src_mac,
                              dest_mac=packet.dest_mac,
                              src_key=packet.src_key,
                              dest_key=packet.dest_key,
                              ptype=packet.ptype,
                              sequence=packet.sequence,
                              vlan=packet.vlan,
                              count=count,
                              offset=offset,
                              length=0,
                              data='')
                self.send_frame(frame, raw_socket)

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
