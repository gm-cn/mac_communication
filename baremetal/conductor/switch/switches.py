from oslo_config import cfg
import logging
import abc
from baremetal.conductor.switch import cisco_ssh, cisco_telnet, huawei_ssh, huawei_telnet

logger = logging.getLogger(__name__)

CONF = cfg.CONF

class AbstractConnection(object):

    def __init__(self):
        self.login_type = CONF.sw_conn.conn_type

    @abc.abstractmethod
    def creat_connection(self):
        pass

class CiscoConnection(AbstractConnection):

    def creat_connection(self):
        if self.login_type == "telnet":
            return cisco_telnet.SwitchPlugin()
        else:
            return cisco_ssh.SwitchPlugin()

class HuaweiConnection(AbstractConnection):

    def creat_connection(self):
        if self.login_type == "telnet":
            return huawei_telnet.SwitchPlugin()
        else:
            return huawei_ssh.SwitchPlugin()

class SwitchConfigure(object):

    def __init__(self):
        self.device_type = CONF.sw_conn.device_type

    def create_plugin(self):
        if self.device_type == "huawei":
            return HuaweiConnection().creat_connection()
        else:
            return CiscoConnection().creat_connection()

def switch_plugin():
    switch_plugin = SwitchConfigure()
    return switch_plugin.create_plugin()