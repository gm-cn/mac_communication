# bms_api v1 url
INIT_IMAGE_PATH = "/baremetal/image/init"
CHANGE_PASSWD_PATH = "/baremetal/changepasswd"
CHANGE_IP_PATH = "/baremetal/changeip"
CLEAN_LOCAL_VOLUMES = "/baremetal/localvolume/clean"
CLONE_IMAGE_PATH = "/baremetal/image/clone"


INIT_SWITCH_CONFIG = "/baremetal/switch/init"
CLEAN_SWITCH_CONFIG = "/baremetal/switch/clean"
SET_VLAN_PATH = "/baremetal/switch/vlan/set"
UNSET_VLAN_PATH = "/baremetal/switch/vlan/unset"
SET_LIMIT_PATH = "/baremetal/switch/limit/set"
UNSET_LIMIT_PATH = "/baremetal/switch/limit/unset"
CREATE_LIMIT_PATH = "/baremetal/switch/limit/create"
DELETE_LIMIT_PATH = "/baremetal/switch/limit/delete"
GET_RELATEION_PATH = "/baremetal/switch/relationship"
SAVE_SWITCH_PATH = "/baremetal/switch/save"

IPMI_STATUS_PATH = "/baremetal/ipmi/status"
IPMI_START_PATH = "/baremetal/ipmi/start"
IPMI_STOP_PATH = "/baremetal/ipmi/stop"
IPMI_RESET_PATH = "/baremetal/ipmi/reset"
GET_LAN1_MAC_PATH = "/baremetal/ipmi/lan1mac"

HOST_SCAN_PATH = "/baremetal/host/scan"
DISK_DELETE_PATH = "/baremetal/disk/delete"

OPEN_PORT_PATH = "/baremetal/port/open"
CLOSE_PORT_PATH = "/baremetal/port/close"

CREATE_PXE_CONFIG_PATH = "/baremetal/pxeconfig/create"
DELETE_PXE_CONFIG_PATH = "/baremetal/pxeconfig/delete"

CONVERT_CUSTOM_IMAGE = "/baremetal/image/convert"

START_SHELLINABOX_CONSOLE = "/baremetal/serial/shellinabox/start"
STOP_SHELLINABOX_CONSOLE = "/baremetal/serial/shellinabox/stop"

CHECK_IMAGE_PATH = "/baremetal/image/check"

BACKUP_IMAGE_PATH = "/baremetal/tpl/backup"

TRANSFER_IMAGE_PATH = "/baremetal/image/transfer"
DELETE_IMAGE_PATH = "/baremetal/image/delete"

TEST = "/pxe/notify/metadata"
DEBUG_PATH = '/debug/result'

# bms_api v2 url
V2_REQUEST_ID = "Taskuuid"
V2_IPMI_STATUS_PATH = "/v2/baremetal/ipmi/status"
V2_IPMI_START_PATH = "/v2/baremetal/ipmi/start"
V2_IPMI_STOP_PATH = "/v2/baremetal/ipmi/stop"
V2_IPMI_RESET_PATH = "/v2/baremetal/ipmi/reset"
V2_IPMI_CHECK_PATH = "/v2/baremetal/ipmi/check"

V2_INIT_SWITCH_CONFIG = "/v2/baremetal/switch/init"
V2_CLEAN_SWITCH_CONFIG = "/v2/baremetal/switch/clean"
V2_SET_VLAN_PATH = "/v2/baremetal/switch/vlan/set"
V2_ALTER_VLAN_PATH = "/v2/baremetal/switch/vlan/alter"
V2_UNSET_VLAN_PATH = "/v2/baremetal/switch/vlan/unset"
V2_SET_LIMIT_PATH = "/v2/baremetal/switch/limit/set"
V2_UNSET_LIMIT_PATH = "/v2/baremetal/switch/limit/unset"
V2_CREATE_LIMIT_PATH = "/v2/baremetal/switch/limit/create"
V2_DELETE_LIMIT_PATH = "/v2/baremetal/switch/limit/delete"
V2_SAVE_SWITCH_PATH = "/v2/baremetal/switch/save"
V2_GET_RELATEION_PATH = "/v2/baremetal/port/mac"
V2_OPEN_PORT_PATH = "/v2/baremetal/port/open"
V2_CLOSE_PORT_PATH = "/v2/baremetal/port/close"
V2_GET_PORT_CFG_PATH = "/v2/baremetal/switch/port/config"

V2_BIOS_ADD_USER_PATH = "/v2/baremetal/ipmi/add_user"
V2_VNC_CONFIG_PATH = "/v2/baremetal/ipmi/vnc"
V2_MAIL_ALARM_PATH = "/v2/baremetal/ipmi/mail_alarm"
V2_SNMP_ALARM_PATH = "/v2/baremetal/ipmi/snmp_alarm"
V2_CPU_PERFORMANCE_PATH = "/v2/baremetal/ipmi/performance"
V2_NUMA_CONFIG_PATH = "/v2/baremetal/ipmi/numa"
V2_GET_SN_BMC_BIOS_PATH = "/v2/baremetal/ipmi/info"
V2_CHECK_SN_PATH = "/v2/baremetal/ipmi/check_sn"
V2_SET_BOOT_TYPE_PATH = "/v2/baremetal/ipmi/boot_set"
V2_GET_MAC_PATH = "/v2/baremetal/ipmi/nic_mac"
V2_PXE_CONFIG_PATH = "/v2/baremetal/ipmi/nic_pxe"
V2_BOOT_CONFIG_PATH = "/v2/baremetal/ipmi/boot_seq"
V2_RAID_CONFIG_PATH = "/v2/baremetal/ipmi/config_raid"
V2_SET_ALARM_CPU_PATH = "/v2/baremetal/ipmi/alarm_cpu"

V2_HARDWARE_TEST_PATH = "/v2/baremetal/hardware_test"
V2_CRC_TEST_PATH = "/v2/baremetal/crc_test"
V2_SW_CRC_PATH= "/v2/baremetal/sw_crc"
V2_HW_LOG_SCP_PATH = "/v2/baremetal/hw_log"
V2_PING_HOST_PATH = "/v2/baremetal/ping"

V2_CHECK_IMAGE_PATH = "/v2/baremetal/image/check"
V2_VNC_CHECK_PATH = "/v2/baremetal/ipmi/vnc_check"
