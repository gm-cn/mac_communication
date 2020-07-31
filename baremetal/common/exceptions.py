class ShellError(Exception):
    def __init__(self, message=None):
        super(ShellError, self).__init__(message)


class BmsCodeMsg(object):
    IPMI_ERROR = [
        {'code': '20001', 'msg': 'Error: Unable to establish IPMI v2 / RMCP+ session'},
        {'code': '20002', 'msg': 'Error in open session response message : insufficient resources for session'},
        {'code': '20003', 'msg': 'Set Session Privilege Level to ADMINISTRATOR failed'},
        {'code': '20004', 'msg': 'network is not connected'}
    ]

    IPMI_STATUS_ERROR = [
        {'code': '20005', 'msg': 'The current power status is inconsistent'}]

    IMAGE_ERROR = [
        {'code': '20011', 'msg': 'The image template is not exist'}
    ]

    BIOS_ERROR = [
        {'code': '20021', 'msg': 'No such file or directory'},
        {'code': '20022', 'msg': 'Error: Unable to establish IPMI v2 / RMCP+ session'},
        {'code': '20023', 'msg': 'The record of sn is false'}
     ]

    HARDWARE_ERROR = [
        {'code': '20031', 'msg': 'No such file or directory'},
        {'code': '20032', 'msg': 'ip list is null'},
        {'code': '20033', 'msg': 'network is not connected'}
    ]

    SWITCH_ERROR = [
        {'code': '20041', 'msg': 'Operational error: Connection time-out'},
        {'code': '20042', 'msg': 'Username or password error'},
        {'code': '20043', 'msg': 'Incomplete command found at '},
        {'code': '20044', 'msg': 'only need one vlan for config dhcp client'},
        {'code': '20045', 'msg': 'port-mac does not exist'}
    ]


class BaremetalError(Exception):
    message = "An unknown exception occurred"

    def __init__(self, **kwargs):
        try:
            self._error_string = self.message % kwargs
        except Exception:
            self._error_string = self.message

    def __str__(self):
        return self._error_string


class BaremetalV2Error(Exception):
    message = "An unknown exception occurred"

    def __init__(self, error_type, **kwargs):
        try:
            self.code = '20071'
            if len(error_type) == 1:
                self.code = error_type[0]['code']
            else:
                for i in error_type:
                    if kwargs['error'] and i['msg'] in kwargs['error']:
                        self.code = i['code']
            self._error_string = self.message % kwargs
        except Exception:
            self._error_string = self.message

    def __str__(self):
        return self._error_string


class ConfigDriveSizeError(BaremetalError):
    message = "baremetal[%(uuid)s] Config drive size exceeds maximum limit of 64MiB."


class CreatePartitionError(BaremetalError):
    message = "create partition for baremetal[%(uuid)s] failed.Error msg:%(error)s."


class IPMIError(BaremetalError):
    message = "execute command %(command)s failed.Error msg:%(error)s"


class PowerStatusError(BaremetalError):
    message = "current power status is not %(status)s ."


class GetVolumePathError(BaremetalError):
    message = "Error msg:%(error)s"

class ImageCheckError(BaremetalError):
    message = "check %(os_version)s failed, error msg: %(error)s"

class VolumeNotFound(BaremetalError):
    message = "volume %(dev_id)s not found."


class PartitionNotFound(BaremetalError):
    message = "partition labeled config-2 was not found."


# Switch Configuration
class ConfigSwitchError(BaremetalError):
    message = "execute command %(command)s failed.Error msg:%(error)s"


class SwitchConnectionError(BaremetalError):
    message = "connect switch %(ip)s failed.Error msg:%(error)s"


class SwitchNetmikoNotSupported(BaremetalError):
    message = "Netmiko does not support device type %(device_type)s"


class SwitchTaskError(BaremetalError):
    message = "performing switch task failed.Error msg:%(error)s."


class CloneImageError(BaremetalError):
    message = "clone image %(src)s to %(dest)s failed.Error msg:%(error)s"

class ConvertCustomImageError(BaremetalError):
    message = "convert custom image from %(src)s to %(dest)s failed.Error msg:%(error)s"

class MakeNfsrootError(BaremetalError):
    message = "make nfsroot for baremetal:%(mac)s failed.Error msg:%(error)s"


class DeletePxeConfigError(BaremetalError):
    message = "delete pxe config for baremetal:%(mac)s failed.Error msg:%(error)s"


class ConfigInternalVlanError(BaremetalError):
    message = "only need one vlan for config dhcp client."


class UnsupportedMode(BaremetalError):
    message = "pxe boot mode:%(mode)s is unsupported."


class StartSerialConsole(BaremetalError):
    message = "host %(ip)s start serial console failed.Error msg:%(error)s"


class BackupImageError(BaremetalError):
    message = "cmd %(command)s backup image failed.Error msg:%(error)s"


class TransferImageError(BaremetalError):
    message = "cmd %(command)s transfer image failed.Error msg:%(error)s"


class CreateMultusError(BaremetalError):
    message = "create multus %(name)s failed. Error msg:%(error)s"


class DeleteMultusError(BaremetalError):
    message = "delete multus %(name)s failed. Error msg:%(error)s"


class Createdeployment(BaremetalError):
    message = "create deployment %(name)s failed. Error msg:%(error)s"


class Deletedeployment(BaremetalError):
    message = "delete deployment %(name)s failed. Error msg:%(error)s"

# add bms_api v2 function
#
# bms_api v2 api
class IPMIV2Error(BaremetalV2Error):
    message = "execute command %(command)s failed.Error msg:%(error)s"


class SetBiosV2Error(BaremetalV2Error):
    message = "host %(ip)s execute %(func)s failed. error msg:%(error)s"


class PowerStatusV2Error(BaremetalV2Error):
    message = "current power status is not %(status)s ."


class SwitchConnectionV2Error(BaremetalV2Error):
    message = "connect switch %(ip)s failed.Error msg:%(error)s"


class ConfigInternalVlanV2Error(BaremetalV2Error):
    message = "only need one vlan for config dhcp client."


class SwitchTaskV2Error(BaremetalV2Error):
    message = "performing switch task failed.Error msg:%(error)s."


class ConfigSwitchV2Error(BaremetalV2Error):
    message = "execute command %(command)s failed.Error msg:%(error)s"


class HardwareTestV2Error(BaremetalV2Error):
    message = "%(func)s test failed. error msg:%(error)s"


class ImageCheckV2Error(BaremetalV2Error):
    message = "check %(os_version)s failed, error msg: %(error)s"

