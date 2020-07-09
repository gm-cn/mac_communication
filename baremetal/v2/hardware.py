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
        self.nginx_ip = CONF.auto_test.nginx_ip
        self.nginx_log = "/var/www/log/bms/hardware_log"
        self.hard_log = "/var/log/cdsstack/hardware_log"
        self.hw_path = os.path.join(self.bios_script, "auto_test")
        self.hw_script = os.path.join(self.hw_path, 'extension.sh ')

    def gen_host_ip_file(self, func, log_id, host_ip):
        logger.debug("The number of servers in this %s test is %s" % (func, len(host_ip)))
        file_path = os.path.join(self.hw_path, 'host_' + log_id)
        if func == "switch_crc":
            file_path = os.path.join(self.hw_path, 'switch_' + log_id)

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

    def gen_logs_content(self, log_id):
        log_path = os.path.join(self.hard_log, log_id)
        if os.path.exists(log_path):
            return log_path
        else:
            os.makedirs(log_path)
        return log_path

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

    def _hardware_test(self, password, log_path, ip_file, ipmi_ip):
        func = 'hardware_test'
        if 'host' in ip_file:
            cmd = "sh " + self.hw_script + func + " '{}' {} --ip_file={} --fix-ip={}"
        else:
            cmd = "sh " + self.hw_script + func + " '{}' {} --ipaddr={} --fix-ip={}"
        logger.debug("execute cmd:  %s" % cmd.format(password, log_path, ip_file, ipmi_ip))
        self.execute_shell(cmd.format(password, log_path, ip_file, ipmi_ip))

    @utils.replyerror_v2
    def hareware_test(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("hardware test taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.HardwareTest()
        rsp.requestId = header[V2_REQUEST_ID]
        log_id = body.log_id if body.log_id else 'default'
        log_path = self.gen_logs_content(log_id)

        func = 'hardware'
        if body.ip_list:
            if len(body.ip_list) == 1:
                ips = body.ip_list[0].split(',')
                ip_file = ips[1]
                ipmi_ip = ips[0]
            else:
                ipmi_ip = ''
                ip_file = self.gen_host_ip_file(func, body.log_id, body.ip_list)

            self._hardware_test(body.password, log_path, ip_file, ipmi_ip)
        else:
            raise exceptions.HardwareTestV2Error(BmsCodeMsg.HARDWARE_ERROR, func=func, error="ip list is null")

        rsp.data['log'] = log_path

        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def crc_test(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("crc test taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.HardwareTest()
        rsp.requestId = header[V2_REQUEST_ID]

        log_id = body.log_id if body.log_id else 'default'
        log_path = self.gen_logs_content(log_id)

        func = 'crc'
        if body.ip_list:
            if len(body.ip_list) == 1:
                raise exceptions.HardwareTestV2Error(BmsCodeMsg.HARDWARE_ERROR, func="crc",
                                                         error="IP list must be more than 1")
            else:
                ip_file = self.gen_host_ip_file(func, body.log_id, body.ip_list)
                cmd = "sh " + self.hw_script + func + " '{}' {} --ip_file={}"
                logger.debug("execute cmd:  %s" % cmd.format(body.password, log_path, ip_file))
                self.execute_shell(cmd.format(body.password, log_path, ip_file))
        else:
            raise exceptions.HardwareTestV2Error(BmsCodeMsg.HARDWARE_ERROR, func=func, error="ip list is null")

        rsp.data['log'] = log_path

        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def switch_crc(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("crc test taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.HardwareTest()
        rsp.requestId = header[V2_REQUEST_ID]
        log_path = self.gen_logs_content(body.log_id)

        func = 'switch_crc'
        if body.ip_list:
            ip_file = self.gen_host_ip_file(func, body.log_id, body.ip_list)
            cmd = "sh " + self.hw_script + func + " '{}' {} --ip_file={}"
            logger.debug("execute cmd:  %s" % cmd.format(password, log_path, ip_file))
            executor = shell.call(cmd.format(password, log_path, ip_file))
            if executor.return_code != 0:
                raise exceptions.HardwareTestV2Error(BmsCodeMsg.HARDWARE_ERROR, fun=func, error=str(executor.stderr))
        else:
            raise exceptions.HardwareTestV2Error(BmsCodeMsg.HARDWARE_ERROR, func=func, error="ip list is null")

        rsp.data['log'] = log_path

        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def hw_log_copy(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("scp test taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.HardwareTest()
        rsp.requestId = header[V2_REQUEST_ID]
        log_id = body.log_id if body.log_id else 'default'
        log_path = os.path.join(self.hard_log, log_id)
        func = "scp_hw_test_log"
        if not os.path.exists(log_path):
            raise exceptions.HardwareTestV2Error(BmsCodeMsg.HARDWARE_ERROR, func=func,
                                                 error="The task id is not exist")
        # cmd = "sshpass -p {} scp -r -o StrictHostKeyChecking=no {} root@{}:{}"
        cmd = "sh " + self.hw_script + func + " '{}' {} --test-type={}"
        executor = shell.call(cmd.format('cds-china', log_path, "hw_log"))
        if executor.return_code != 0:
            raise exceptions.HardwareTestV2Error(BmsCodeMsg.HARDWARE_ERROR, func=func, error=str(executor.stderr))

        rsp.data['log'] = log_path

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
