import logging
import os
import tenacity
import json
import time
from concurrent.futures import ThreadPoolExecutor
from baremetal.common import jsonobject, utils, http, shell
from baremetal.conductor import models
from baremetal.common import exceptions

logger = logging.getLogger(__name__)

ON_AFTER_PXE = ['R540']
retry_kwargs = {
            "after": tenacity.after_log(logger, logging.DEBUG),
            "reraise": True,
            "wait": tenacity.wait_random(min=3, max=4),
            "stop": tenacity.stop_after_attempt(4)}


class IPMIPlugin(object):

    def __init__(self):
        self.base_cmd = "ipmitool -I lanplus -H {} -U {} -P {} "
        self.cmd = "ipmitool -I lanplus -H {} -U {} -P {} chassis "
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
            raise exceptions.IPMIError(command=ipmi_cmd, error=str(executor.stderr))

        if self.ensure_power_status(host, status):
            logger.debug("host:%s power %s successfully." % (host.ip, status))
        else:
            raise exceptions.PowerStatusError(status=status)

    @tenacity.retry(**retry_kwargs)
    def get_server_type(self, host):
        server_type_cmd = self.server_type_cmd.format(host.ip, host.username, host.password)
        executor = shell.call(server_type_cmd)
        if executor.return_code != 0:
            raise exceptions.IPMIError(command=server_type_cmd, error=executor.stderr)
        output = executor.stdout.replace('\n', '')
        server_type = output.split(':')[-1]
        logger.debug("%s server type is %s" % (host.ip, server_type.strip()))
        return server_type.strip()

    @tenacity.retry(**retry_kwargs)
    def check_status(self, rsp, host):
        power_status_cmd = self.power_status_cmd.format(host.ip, host.username, host.password)
        executor = shell.call(power_status_cmd, logcmd=False)
        if executor.return_code != 0:
            raise exceptions.IPMIError(command=power_status_cmd, error=executor.stderr)
        output = executor.stdout.replace('\n', '')
        logger.debug("host:%s power status:%s." % (host.ip, output))
        if "on" in output:
            rsp.status.append({"host": host.ip, "status": "on"})
        elif "off" in output:
            rsp.status.append({"host": host.ip, "status": "off"})
        else:
            logger.debug("host:%s power status failed" % host.ip)

    @utils.replyerror
    def status(self, req):
        # body = jsonobject.loads(req[http.REQUEST_BODY])
        rsp = models.IPMIResponse()
        new_body = utils.list_dict_duplicate_removal(json.loads(req[http.REQUEST_BODY]))
        body = jsonobject.loads(json.dumps(new_body))
        logger.debug("ipmi status body:%s" % json.dumps(new_body))
        with ThreadPoolExecutor(max_workers=100) as executor:
            for host in body:
                executor.submit(self.check_status, rsp, host)
        return jsonobject.dumps(rsp)

    @utils.replyerror
    def poweroff(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        logger.debug("ipmi stop body:%s" % req[http.REQUEST_BODY])
        rsp = models.IPMIResponse()

        @tenacity.retry(**retry_kwargs)
        def _check_out(cmd):
            exec_cmd = shell.call(cmd)
            time.sleep(1)
            if exec_cmd.return_code != 0:
                raise exceptions.IPMIError(command=cmd, error=exec_cmd.stderr)
            return exec_cmd.stdout.replace('\n', '')

        for host in body:
            power_status_cmd = self.power_status_cmd.format(host.ip, host.username, host.password)
            output = _check_out(power_status_cmd)
            if "on" in output:
                power_off_cmd = self.poweroff_cmd.format(host.ip, host.username, host.password)
                self.ipmi_power(power_off_cmd, host, 'off')
        return jsonobject.dumps(rsp)

    @utils.replyerror
    def reset(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        logger.debug("ipmi stop  body:%s" % req[http.REQUEST_BODY])

        @tenacity.retry(**retry_kwargs)
        def _check_out(cmd):
            exec_cmd = shell.call(cmd)
            time.sleep(1)
            if exec_cmd.return_code != 0:
                raise exceptions.IPMIError(command=cmd, error=exec_cmd.stderr)
            return exec_cmd.stdout.replace('\n', '')
        rsp = models.AgentResponse()

        for host in body:
            server_type = self.get_server_type(host)

            power_off_cmd = self.poweroff_cmd.format(host.ip, host.username, host.password)
            self.ipmi_power(power_off_cmd, host, 'off')

            set_boot_cmd = self.bootdev_cmd.format(host.ip, host.username, host.password, "disk")

            count_num = [t for t in ON_AFTER_PXE if t in server_type]
            if len(count_num) == 0:
                _check_out(set_boot_cmd)

            power_on_cmd = self.poweron_cmd.format(host.ip, host.username, host.password)
            try:
                self.ipmi_power(power_on_cmd, host, 'on')
            except exceptions.IPMIError as e:
                if "not supported in present state" in str(e):
                    logger.debug("Ignore the error: %s" % str(e))
                else:
                    raise e

            if len(count_num) > 0:
                _check_out(set_boot_cmd)

        return jsonobject.dumps(rsp)

    @utils.replyerror
    def host_scan(self, req):
        rsp = models.IPMIResponse()
        mount_cmd = "mount -o remount,rw /sys/"
        executor = shell.call(mount_cmd)
        if executor.return_code != 0:
            raise exceptions.IPMIError(command=mount_cmd, error=str(executor.stderr))
        scan_cmd = 'echo "- - -" > /sys/class/scsi_host/%s/scan'
        hosts = ["host0", "host1"]
        for host in hosts:
            cmd = scan_cmd % host
            executor = shell.call(cmd)
            if executor.return_code != 0:
                raise exceptions.IPMIError(command=cmd, error=str(executor.stderr))

        return jsonobject.dumps(rsp)

    @utils.replyerror
    def host_delete_disk(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        logger.debug("host scan body:%s" % req[http.REQUEST_BODY])
        rsp = models.IPMIResponse()
        mount_cmd = "mount -o remount,rw /sys/"
        executor = shell.call(mount_cmd)
        if executor.return_code != 0:
            raise exceptions.IPMIError(command=mount_cmd, error=str(executor.stderr))

        volume_path = utils.get_volume_path(body.dev_id)
        device = os.path.realpath(volume_path)
        executor = shell.call("echo 1 > /sys/block/%s/device/delete" % device.split("/")[2])
        if executor.return_code != 0:
            raise exceptions.IPMIError(command="delete disk", error=str(executor.stderr))

        return jsonobject.dumps(rsp)

    @utils.replyerror
    def poweron(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        logger.debug("ipmi poweron body:%s" % req[http.REQUEST_BODY])

        @tenacity.retry(**retry_kwargs)
        def _check_out(cmd):
            exec_cmd = shell.call(cmd)
            time.sleep(1)
            if exec_cmd.return_code != 0:
                raise exceptions.IPMIError(command=cmd, error=exec_cmd.stderr)
            return exec_cmd.stdout.replace('\n', '')

        rsp = models.IPMIResponse()
        for host in body:
            server_type = self.get_server_type(host)

            power_status_cmd = self.power_status_cmd.format(host.ip, host.username, host.password)
            output = _check_out(power_status_cmd)
            if "on" in output:
                power_off_cmd = self.poweroff_cmd.format(host.ip, host.username, host.password)
                self.ipmi_power(power_off_cmd, host, 'off')

            mode = "pxe" if host.mode and host.mode in ["uefi", "bios"] else "disk"
            set_boot_cmd =self.bootdev_cmd.format(host.ip, host.username, host.password, mode)
            if host.mode == "uefi":
                set_boot_cmd += " options=efiboot"

            count_num = [t for t in ON_AFTER_PXE if t in server_type]
            if len(count_num) == 0:
                _check_out(set_boot_cmd)

            power_on_cmd = self.poweron_cmd.format(host.ip, host.username, host.password)
            try:
                self.ipmi_power(power_on_cmd, host, 'on')
            except exceptions.IPMIError as e:
                if "not supported in present state" in str(e):
                    logger.debug("Ignore the error: %s" % str(e))
                else:
                    raise e

            if len(count_num) > 0:
                _check_out(set_boot_cmd)

        return jsonobject.dumps(rsp)

    @utils.replyerror
    def get_lan1_mac(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        logger.debug("get onboard nic mac body:%s" % req[http.REQUEST_BODY])
        rsp = models.GetLan1MACResponse()
        macs = []
        for host in body:
            mac_info = {}
            # inspur
            get_lan1_mac_cmd = "ipmitool -I lanplus -H %s -U %s -P %s raw 0x3a 0x02 0x04 0x00 0x00"
            executor = shell.call(get_lan1_mac_cmd % (host.ip, host.username, host.password))
            lan1_mac = ":".join([item for item in executor.stdout.split(" ")[6:12]])
            mac_info.update({"ip": host.ip, "lan1_mac": lan1_mac})
            macs.append(mac_info)
        rsp.macs = macs
        return jsonobject.dumps(rsp)

    def start_sol_console_cmd(self, param):
        logger.debug("get sol param:%s" % param)
        activate_sol = self.base_cmd + "sol activate"
        start_sol = activate_sol.format(param.ip, param.username, param.password)
        logger.debug("start sol command:%s" % start_sol)
        return start_sol

    def stop_sol_console_cmd(self, param):
        logger.debug("get sol param:%s" % param)
        deactivate_sol = self.base_cmd + "sol deactivate"
        stop_sol = deactivate_sol.format(param.ip, param.username, param.password)
        logger.debug("stop sol command:%s" % stop_sol)
        return stop_sol
