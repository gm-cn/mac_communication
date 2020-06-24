import logging
import tenacity
import time
import subprocess
import os
from oslo_config import cfg

from baremetal.common import jsonobject, utils, http, shell
from baremetal.v2 import models
from baremetal.common import exceptions
from baremetal.common.exceptions import BmsCodeMsg
from baremetal.constants import V2_REQUEST_ID

logger = logging.getLogger(__name__)
CONF = cfg.CONF

retry_kwargs = {
            "after": tenacity.after_log(logger, logging.DEBUG),
            "reraise": True,
            "wait": tenacity.wait_random(min=15, max=20),
            "stop": tenacity.stop_after_attempt(20)}


class HarewarePlugin_v2(object):

    def __init__(self):
        self.bios_script = CONF.auto_test.bios_set
        self.hw_path = os.path.join(self.bios_script, "auto_test")
        self.hw_script = os.path.join(self.hw_path, 'extension.sh ')

    def gen_host_ip_file(self, func, host_ip):
        logger.debug("The number of servers in this %s test is %s" % (func, len(host_ip)))
        file_path = os.path.join(self.hw_path, 'host_' + func)
        with open(file_path, 'w') as fp:
            for i in host_ip:
                ips = i.split(',')
                fp.write(' '.join(ips) + '\n')
        return file_path

    def execute_shell(self, cmd):
        subprocess.Popen(cmd, shell=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         close_fds=True,
                         executable='/bin/bash')

    def _disk_test(self, password, ip_file):
        func = 'disk_test'
        if 'host' in ip_file:
            cmd = "sh " + self.hw_script + func + " '{}' --ip_file={}"
        else:
            cmd = "sh " + self.hw_script + func + " '{}' --ipaddr={}"
        logger.debug("execute cmd:  %s" % cmd.format(password, ip_file))
        self.execute_shell(cmd.format(password, ip_file))

    def _cpu_test(self, password, ip_file):
        func = 'cpu_test'
        if 'host' in ip_file:
            cmd = "sh " + self.hw_script + func + " '{}' --ip_file={}"
        else:
            cmd = "sh " + self.hw_script + func + " '{}' --ipaddr={}"
        logger.debug("execute cmd:  %s" % cmd.format(password, ip_file))
        self.execute_shell(cmd.format(password, ip_file))

    def _mem_test(self, password, ip_file):
        func = 'mem'
        if 'host' in ip_file:
            cmd = "sh " + self.hw_script + func + " '{}' --mem_size=255.5G --ip_file={}"
        else:
            cmd = "sh " + self.hw_script + func + " '{}' --mem_size=255.5G --ipaddr={}"
        logger.debug("execute cmd:  %s" % cmd.format(password, ip_file))
        self.execute_shell(cmd.format(password, ip_file))

    def _hardware_test(self, password, ip_file):
        func = 'hardware_test'
        if 'host' in ip_file:
            cmd = "sh " + self.hw_script + func + " '{}' --ip_file={}"
        else:
            cmd = "sh " + self.hw_script + func + " '{}' --ipaddr={}"
        logger.debug("execute cmd:  %s" % cmd.format(password, ip_file))
        self.execute_shell(cmd.format(password, ip_file))

    @utils.replyerror_v2
    def hareware_test(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("hardware test taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.HardwareTest()
        rsp.requestId = header[V2_REQUEST_ID]

        func = 'hardware'
        if body.ip_list:
            if len(body.ip_list) == 1:
                ips = body.ip_list[0].split(',')
                ip_file = ips[0]
                cmd = "sh " + self.hw_script + "check_ssh '{}' --ipaddr={}"
                executor = shell.call(cmd.format(body.password, ip_file))
                if executor.return_code != 0:
                    raise exceptions.HardwareTestV2Error(BmsCodeMsg.HARDWARE_ERROR, func="check_ssh",
                                                         error=str(executor.stderr))
            else:
                ip_file = self.gen_host_ip_file(func, body.ip_list)

            self._hardware_test(body.password, ip_file)
        else:
            raise exceptions.HardwareTestV2Error(BmsCodeMsg.HARDWARE_ERROR, func=func, error="ip list is null")

        rsp.data['log'] = self.hw_path

        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def ping_host(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("ping host taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.BiosconfigSet()
        rsp.requestId = header[V2_REQUEST_ID]

        @tenacity.retry(**retry_kwargs)
        def _ping_host(ip):
            response = os.system("ping -c 1 " + ip)
            if response == 0:
                logger.debug("network is connected.")
                return
            else:
                raise exceptions.HardwareTestV2Error(BmsCodeMsg.HARDWARE_ERROR, func="ping",
                                                     error="network is not connected")
        if body.server_ip:
            _ping_host(body.server_ip)
        else:
            raise exceptions.HardwareTestV2Error(BmsCodeMsg.HARDWARE_ERROR, func="ping",
                                                 error="host ip is null")
        return jsonobject.dumps(rsp)
