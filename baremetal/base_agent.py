import logging

from oslo_config import cfg

from baremetal import opts, constants
from baremetal.common import http, daemon
from baremetal.conductor.baremetals import BaremetalPlugin
from baremetal.conductor.debug_plugin import DebugPlugin
from baremetal.conductor.ipmi import IPMIPlugin
from baremetal.conductor.pxe import PxePlugin
from baremetal.conductor.switch.switches import switch_plugin as SwitchPlugin
from baremetal.conductor.image import ImagePlugin
from baremetal.conductor.kube import KubePlugin
from baremetal.v2.image import ImagePlugin_v2
from baremetal.v2.switch.switches import switch_plugin_v2 as SwitchPlugin_v2
from baremetal.conductor.serialconsole import SerialConsolePlugin
from baremetal.v2.ipmi import IPMIPlugin_v2
from baremetal.v2.bios import BiosSetPlugin_v2
from baremetal.v2.hardware import HarewarePlugin_v2

logger = logging.getLogger(__name__)
_rest_service = None

CONF = cfg.CONF


def new_rest_service(config={}):
    global _rest_service
    if not _rest_service:
        _rest_service = RestService(config)
    return _rest_service


class RestService(object):
    def register_path(self):
        self.rest.register_sync_uri(constants.HEALTH,
                                     self.baremetal.health)
        self.rest.register_async_uri(constants.INIT_IMAGE_PATH,
                                     self.baremetal.init_image)
        self.rest.register_async_uri(constants.SET_VLAN_PATH,
                                     self.switches.set_vlan)
        self.rest.register_async_uri(constants.UNSET_VLAN_PATH,
                                     self.switches.unset_vlan)
        self.rest.register_async_uri(constants.SET_LIMIT_PATH,
                                     self.switches.set_limit)
        self.rest.register_async_uri(constants.UNSET_LIMIT_PATH,
                                     self.switches.unset_limit)
        self.rest.register_async_uri(constants.CREATE_LIMIT_PATH,
                                     self.switches.create_limit_template)
        self.rest.register_async_uri(constants.DELETE_LIMIT_PATH,
                                     self.switches.delete_limit_template)
        self.rest.register_async_uri(constants.CHANGE_IP_PATH,
                                     self.baremetal.change_ip),
        self.rest.register_async_uri(constants.CHANGE_PASSWD_PATH,
                                     self.baremetal.change_passwd)
        self.rest.register_sync_uri(constants.IPMI_STATUS_PATH,
                                    self.ipmi.status)
        self.rest.register_async_uri(constants.IPMI_START_PATH,
                                     self.ipmi.poweron)
        self.rest.register_async_uri(constants.IPMI_STOP_PATH,
                                     self.ipmi.poweroff)
        self.rest.register_async_uri(constants.IPMI_RESET_PATH,
                                     self.ipmi.reset)
        self.rest.register_sync_uri(constants.HOST_SCAN_PATH,
                                    self.ipmi.host_scan)
        self.rest.register_async_uri(constants.DISK_DELETE_PATH,
                                     self.ipmi.host_delete_disk)
        self.rest.register_async_uri(constants.GET_LAN1_MAC_PATH,
                                     self.ipmi.get_lan1_mac)
        self.rest.register_async_uri(constants.OPEN_PORT_PATH,
                                     self.switches.open_port)
        self.rest.register_async_uri(constants.CLOSE_PORT_PATH,
                                     self.switches.close_port)
        self.rest.register_async_uri(constants.INIT_SWITCH_CONFIG,
                                     self.switches.init_all_config)
        self.rest.register_async_uri(constants.CLEAN_SWITCH_CONFIG,
                                     self.switches.clean_all_config)
        self.rest.register_async_uri(constants.GET_RELATEION_PATH,
                                     self.switches.get_relations)
        self.rest.register_sync_uri(constants.SAVE_SWITCH_PATH,
                                     self.switches.save)
        self.rest.register_async_uri(constants.CLONE_IMAGE_PATH,
                                     self.baremetal.clone_image)
        self.rest.register_async_uri(constants.CREATE_PXE_CONFIG_PATH,
                                     self.pxe.pxe_prepare)
        self.rest.register_async_uri(constants.DELETE_PXE_CONFIG_PATH,
                                     self.pxe.pxe_post)
        self.rest.register_async_uri(constants.CONVERT_CUSTOM_IMAGE,
                                     self.pxe.convert_image_format)
        self.rest.register_sync_uri(constants.TEST,
                                    self.pxe.test)
        self.rest.register_sync_uri(constants.DEBUG_PATH,
                                    self.debug.debug)
        self.rest.register_sync_uri(constants.START_SHELLINABOX_CONSOLE,
                                     self.serial.start_shellinabox_console)
        self.rest.register_sync_uri(constants.STOP_SHELLINABOX_CONSOLE,
                                     self.serial.stop_shellinabox_console)
        self.rest.register_sync_uri(constants.CHECK_IMAGE_PATH,
                                     self.img.checkout_image)
        self.rest.register_sync_uri(constants.BACKUP_IMAGE_PATH,
                                     self.img.backup_image)
        self.rest.register_async_uri(constants.TRANSFER_IMAGE_PATH,
                                     self.img.transfer_image)
        self.rest.register_async_uri(constants.DELETE_IMAGE_PATH,
                                     self.img.delete_image)
        self.rest.register_async_uri(constants.CREATE_MULTUS,
                                     self.kube.create_multus)
        self.rest.register_async_uri(constants.DELETE_MULTUS,
                                     self.kube.delete_multus)
        self.rest.register_async_uri(constants.CREATE_MON,
                                     self.kube.create_deployment)
        self.rest.register_async_uri(constants.DELETE_MON,
                                     self.kube.delete_deployment)

    # bms_api v2 api

    def register_v2_path(self):
        # ipmi power
        self.rest.register_async_uri(constants.V2_IPMI_STOP_PATH,
                                     self.ipmi_v2.poweroff)
        self.rest.register_async_uri(constants.V2_IPMI_START_PATH,
                                     self.ipmi_v2.poweron)
        self.rest.register_async_uri(constants.V2_IPMI_RESET_PATH,
                                     self.ipmi_v2.reset)
        self.rest.register_sync_uri(constants.V2_IPMI_STATUS_PATH,
                                    self.ipmi_v2.status)
        self.rest.register_sync_uri(constants.V2_IPMI_CHECK_PATH,
                                    self.ipmi_v2.check_ipmi)
        # switch
        self.rest.register_async_uri(constants.V2_OPEN_PORT_PATH,
                                     self.switches_v2.open_port)
        self.rest.register_async_uri(constants.V2_CLOSE_PORT_PATH,
                                     self.switches_v2.close_port)
        self.rest.register_async_uri(constants.V2_INIT_SWITCH_CONFIG,
                                     self.switches_v2.init_all_config)
        self.rest.register_async_uri(constants.V2_CLEAN_SWITCH_CONFIG,
                                     self.switches_v2.clean_all_config)
        self.rest.register_async_uri(constants.V2_GET_RELATEION_PATH,
                                     self.switches_v2.get_relations)
        self.rest.register_async_uri(constants.V2_SET_VLAN_PATH,
                                     self.switches_v2.set_vlan)
        self.rest.register_sync_uri(constants.V2_ALTER_VLAN_PATH,
                                     self.switches_v2.alter_vlan)
        self.rest.register_async_uri(constants.V2_UNSET_VLAN_PATH,
                                     self.switches_v2.unset_vlan)
        self.rest.register_async_uri(constants.V2_SET_LIMIT_PATH,
                                     self.switches_v2.set_limit)
        self.rest.register_async_uri(constants.V2_UNSET_LIMIT_PATH,
                                     self.switches_v2.unset_limit)
        self.rest.register_async_uri(constants.V2_CREATE_LIMIT_PATH,
                                     self.switches_v2.create_limit_template)
        self.rest.register_async_uri(constants.V2_DELETE_LIMIT_PATH,
                                     self.switches_v2.delete_limit_template)
        self.rest.register_sync_uri(constants.V2_SAVE_SWITCH_PATH,
                                     self.switches_v2.save)
        self.rest.register_async_uri(constants.V2_GET_PORT_CFG_PATH,
                                     self.switches_v2.get_port_config)
        self.rest.register_async_uri(constants.V2_SWITCH_SN_PATH,
                                     self.switches_v2.get_switch_sn)
        # bios set
        self.rest.register_async_uri(constants.V2_BIOS_ADD_USER_PATH,
                                     self.bios_v2.add_bmc_user)
        self.rest.register_async_uri(constants.V2_VNC_CONFIG_PATH,
                                     self.bios_v2.vnc_config)
        self.rest.register_async_uri(constants.V2_MAIL_ALARM_PATH,
                                     self.bios_v2.mail_alarm)
        self.rest.register_async_uri(constants.V2_SNMP_ALARM_PATH,
                                     self.bios_v2.snmp_alarm)
        self.rest.register_async_uri(constants.V2_CPU_PERFORMANCE_PATH,
                                     self.bios_v2.performance_config)
        self.rest.register_async_uri(constants.V2_NUMA_CONFIG_PATH,
                                     self.bios_v2.numa_config)
        self.rest.register_sync_uri(constants.V2_GET_SN_BMC_BIOS_PATH,
                                     self.bios_v2.get_sn)
        self.rest.register_sync_uri(constants.V2_CHECK_SN_PATH,
                                    self.bios_v2.sn_check)
        self.rest.register_async_uri(constants.V2_SET_BOOT_TYPE_PATH,
                                     self.bios_v2.boot_set)
        self.rest.register_async_uri(constants.V2_GET_MAC_PATH,
                                     self.bios_v2.get_mac)
        self.rest.register_async_uri(constants.V2_PXE_CONFIG_PATH,
                                     self.bios_v2.pxe_config)
        self.rest.register_async_uri(constants.V2_BOOT_CONFIG_PATH,
                                     self.bios_v2.boot_config)
        self.rest.register_async_uri(constants.V2_RAID_CONFIG_PATH,
                                     self.bios_v2.config_raid)
        self.rest.register_async_uri(constants.V2_SET_ALARM_CPU_PATH,
                                     self.bios_v2.set_alarm_and_cpu)
        self.rest.register_sync_uri(constants.V2_VNC_CHECK_PATH,
                                     self.bios_v2.vnc_check)
        self.rest.register_async_uri(constants.V2_HARDWARE_TEST_PATH,
                                     self.hardware_v2.hareware_test)
        self.rest.register_async_uri(constants.V2_CRC_TEST_PATH,
                                     self.hardware_v2.crc_test)
        self.rest.register_sync_uri(constants.V2_HW_LOG_SCP_PATH,
                                    self.hardware_v2.hw_log_copy)
        self.rest.register_async_uri(constants.V2_PING_HOST_PATH,
                                     self.hardware_v2.ping_host)
        self.rest.register_sync_uri(constants.V2_CHECK_IMAGE_PATH,
                                     self.img_v2.checkout_image)
        self.rest.register_async_uri(constants.V2_BIOS_UPDATE_PATH,
                                    self.bios_v2.bios_update)
        self.rest.register_async_uri(constants.V2_IDRAC_UPDATE_PATH,
                                    self.bios_v2.idrac_update)
        self.rest.register_async_uri(constants.V2_DOWNLOAD_FILE_PATH,
                                     self.bios_v2.download_file)

    def __init__(self, config):
        opts.register_all_options()
        opts.prepare()
        self.rest = http.HttpServer(port=CONF.server_port)
        self.config = config
        self.baremetal = BaremetalPlugin()
        self.switches = SwitchPlugin()
        self.ipmi = IPMIPlugin()
        self.pxe = PxePlugin()
        self.img = ImagePlugin()
        self.debug = DebugPlugin()
        self.serial = SerialConsolePlugin()
        self.kube = KubePlugin()

        self.img_v2 = ImagePlugin_v2()
        self.ipmi_v2 = IPMIPlugin_v2()
        self.bios_v2 = BiosSetPlugin_v2()
        self.hardware_v2 = HarewarePlugin_v2()
        self.switches_v2 = SwitchPlugin_v2()

    def start(self, in_thread=True):
        self.register_path()
        self.register_v2_path()
        if in_thread:
            self.rest.start_in_thread()
        else:
            self.rest.start()


class BaremetalDaemon(daemon.Daemon):
    def run(self):
        self.agent = new_rest_service()
        self.agent.start(in_thread=False)
