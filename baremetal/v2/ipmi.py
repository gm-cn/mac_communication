import logging
import tenacity
import os
import time
from baremetal.common import jsonobject, utils, http, shell
from baremetal.v2 import models
from baremetal.common import exceptions
from baremetal.common.exceptions import BmsCodeMsg
from baremetal.constants import V2_REQUEST_ID

logger = logging.getLogger(__name__)

ON_AFTER_PXE = ['R540']
retry_kwargs = {
            "after": tenacity.after_log(logger, logging.DEBUG),
            "reraise": True,
            "wait": tenacity.wait_random(min=2, max=5),
            "stop": tenacity.stop_after_attempt(5)}


class IPMIPlugin_v2(object):

    def __init__(self):
        self.base_cmd = "ipmitool -I lanplus -H {} -U {} -P '{}' "
        self.cmd = "ipmitool -I lanplus -H {} -U {} -P '{}' chassis "
        self.power_status_cmd = self.cmd + "power status"
        self.poweron_cmd = self.cmd + "power on"
        self.poweroff_cmd = self.cmd + "power off"
        self.bootdev_cmd = self.cmd + "bootdev {}"
        self.server_type_cmd = self.base_cmd + "fru |grep 'Product Name'"

    def ensure_power_status(self, host, status):
        power_status_cmd = self.power_status_cmd.format(host.ip, host.username, host.password)
        count = 0
        while count < 6:
            executor = shell.call(power_status_cmd, logcmd=False)
            if status in executor.stdout:
                return True
            else:
                logger.debug("host:%s power status %s" % (host.ip, executor.stdout.replace('\n', '')))
                count += 1
                time.sleep(count)
        return False

    @tenacity.retry(**retry_kwargs)
    def ipmi_power(self, ipmi_cmd, host, status):
        executor = shell.call(ipmi_cmd)
        if executor.return_code != 0:
            if "not supported in present state" in str(executor.stderr):
                logger.debug("Ignore the error: %s" % str(executor.stderr))
            else:
                raise exceptions.IPMIV2Error(BmsCodeMsg.IPMI_ERROR, command=ipmi_cmd, error=str(executor.stderr))

        if self.ensure_power_status(host, status):
            logger.debug("host:%s power %s successfully." % (host.ip, status))
        else:
            raise exceptions.PowerStatusV2Error(BmsCodeMsg.IPMI_STATUS_ERROR, status=status)

    @tenacity.retry(**retry_kwargs)
    def get_server_type(self, host):
        server_type_cmd = self.server_type_cmd.format(host.ip, host.username, host.password)
        executor = shell.call(server_type_cmd)
        if executor.return_code != 0:
            raise exceptions.IPMIV2Error(BmsCodeMsg.IPMI_ERROR, command=server_type_cmd, error=executor.stderr)
        output = executor.stdout.replace('\n', '')
        server_type = output.split(':')[-1]
        logger.debug("%s server type is %s" % (host.ip, server_type.strip()))
        return server_type.strip()

    @tenacity.retry(**retry_kwargs)
    def _check_out(self, cmd):
        exec_cmd = shell.call(cmd)
        time.sleep(1)
        if exec_cmd.return_code != 0:
            raise exceptions.IPMIV2Error(BmsCodeMsg.IPMI_ERROR, command=cmd, error=exec_cmd.stderr)
        return exec_cmd.stdout.replace('\n', '')

    @tenacity.retry(**retry_kwargs)
    def check_status(self, rsp, host):
        power_status_cmd = self.power_status_cmd.format(host.ip, host.username, host.password)
        executor = shell.call(power_status_cmd, logcmd=False)
        if executor.return_code != 0:
            raise exceptions.IPMIV2Error(BmsCodeMsg.IPMI_ERROR, command=power_status_cmd, error=executor.stderr)
        output = executor.stdout.replace('\n', '')
        logger.debug("host:%s power status:%s." % (host.ip, output))
        if "on" in output:
            rsp.data = {"host": host.ip, "status": "on"}
        elif "off" in output:
            rsp.data = {"host": host.ip, "status": "off"}

    @utils.replyerror_v2
    def status(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("ipmi status taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.IPMIStatusResponse()
        rsp.requestId = header[V2_REQUEST_ID]

        self.check_status(rsp, body)

        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def poweroff(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("ipmi stop taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.IPMIResponse()
        rsp.requestId = header[V2_REQUEST_ID]

        power_status_cmd = self.power_status_cmd.format(body.ip, body.username, body.password)
        output = self._check_out(power_status_cmd)
        if "on" in output:
            power_off_cmd = self.poweroff_cmd.format(body.ip, body.username, body.password)
            self.ipmi_power(power_off_cmd, body, 'off')
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def reset(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("ipmi reset taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.AgentResponse()
        rsp.requestId = header[V2_REQUEST_ID]

        server_type = self.get_server_type(body)

        power_status_cmd = self.power_status_cmd.format(body.ip, body.username, body.password)
        output = self._check_out(power_status_cmd)
        if "on" in output:
            power_off_cmd = self.poweroff_cmd.format(body.ip, body.username, body.password)
            self.ipmi_power(power_off_cmd, body, 'off')

        set_boot_cmd = self.bootdev_cmd.format(body.ip, body.username, body.password, "disk")

        count_num = [t for t in ON_AFTER_PXE if t in server_type]
        if len(count_num) == 0:
            self._check_out(set_boot_cmd)

        power_on_cmd = self.poweron_cmd.format(body.ip, body.username, body.password)
        try:
            self.ipmi_power(power_on_cmd, body, 'on')
        except exceptions.IPMIV2Error as e:
            if "not supported in present state" in str(e):
                logger.debug("Ignore the error: %s" % str(e))
            else:
                raise e

        if len(count_num) > 0:
            self._check_out(set_boot_cmd)

        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def poweron(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("ipmi poweron taskuuid:%s body: %s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.IPMIResponse()
        rsp.requestId = header[V2_REQUEST_ID]

        server_type = self.get_server_type(body)

        power_status_cmd = self.power_status_cmd.format(body.ip, body.username, body.password)
        output = self._check_out(power_status_cmd)
        if "on" in output:
            power_off_cmd = self.poweroff_cmd.format(body.ip, body.username, body.password)
            self.ipmi_power(power_off_cmd, body, 'off')

        mode = "pxe" if body.mode and body.mode in ["uefi", "bios"] else "disk"
        set_boot_cmd = self.bootdev_cmd.format(body.ip, body.username, body.password, mode)
        if body.mode == "uefi":
            set_boot_cmd += " options=efiboot"

        count_num = [t for t in ON_AFTER_PXE if t in server_type]
        if len(count_num) == 0:
            self._check_out(set_boot_cmd)

        power_on_cmd = self.poweron_cmd.format(body.ip, body.username, body.password)
        try:
            self.ipmi_power(power_on_cmd, body, 'on')
        except exceptions.IPMIV2Error as e:
            if "not supported in present state" in str(e):
                logger.debug("Ignore the error: %s" % str(e))
            else:
                raise e

        if len(count_num) > 0:
            self._check_out(set_boot_cmd)

        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def check_ipmi(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("check ipmi taskuuid:%s body: %s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.IPMIResponse()
        rsp.requestId = header[V2_REQUEST_ID]

        @tenacity.retry(reraise=True,
                        wait=tenacity.wait_fixed(1),
                        stop=tenacity.stop_after_attempt(4))
        def _ping_host(ip):
            response = os.system("ping -c 1 " + ip)
            if response == 0:
                logger.debug("network is connected.")
                return True
            else:
                raise exceptions.IPMIV2Error(BmsCodeMsg.IPMI_ERROR, command='ping -c 1 %s' % ip,
                                             error="network is not connected")

        if _ping_host(body.ip):
            power_status_cmd = self.power_status_cmd.format(body.ip, body.username, body.password)
            self._check_out(power_status_cmd)

        return jsonobject.dumps(rsp)
