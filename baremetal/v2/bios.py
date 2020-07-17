import logging
import os
import requests
from oslo_config import cfg

from baremetal.v2 import models
from baremetal.constants import V2_REQUEST_ID
from baremetal.common import shell, exceptions
from baremetal.common.exceptions import BmsCodeMsg
from baremetal.common import jsonobject, utils, http

logger = logging.getLogger(__name__)
CONF = cfg.CONF


class BiosSetPlugin_v2(object):

    def __init__(self):
        self.bios_script = CONF.auto_test.bios_set
        self.update_file = os.path.join(CONF.pxe.tftpboot_dir, "update_file")
        self.bios_set = os.path.join(self.bios_script, "ipmi/ipmi_function.sh ")

    def execute_cmd(self, func, body):
        cmd = "sh " + self.bios_set + func + " {} '{}' --ipaddr={}"
        logger.debug("execute cmd:  %s" % cmd.format(body.username, body.password, body.ip))
        executor = shell.call(cmd.format(body.username, body.password, body.ip))

        if executor.return_code != 0:
            raise exceptions.SetBiosV2Error(BmsCodeMsg.BIOS_ERROR, ip=body.ip, func=func, error=str(executor.stderr))

    @utils.replyerror_v2
    def add_bmc_user(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("add bmc user taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.BiosconfigSet()
        rsp.requestId = header[V2_REQUEST_ID]

        func = 'add_bmc_user'
        cmd = "sh " + self.bios_set + func + " {} '{}' --ipaddr={} --username={} --userpassword='{}'"
        executor = shell.call(cmd.format(body.adminname, body.adminpassword, body.ip, body.username, body.userpassword))
        if executor.return_code != 0:
            raise exceptions.SetBiosV2Error(BmsCodeMsg.BIOS_ERROR, ip=body.ip, func=func, error=str(executor.stderr))
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def vnc_config(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("vnc config taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.BiosconfigSet()
        rsp.requestId = header[V2_REQUEST_ID]

        func = 'vnc_config'
        cmd = "sh " + self.bios_set + func + " {} '{}' --ipaddr={} --vnc_password='{}'"
        executor = shell.call(cmd.format(body.username, body.password, body.ip, body.vnc_password))
        if executor.return_code != 0:
            raise exceptions.SetBiosV2Error(BmsCodeMsg.BIOS_ERROR, ip=body.ip, func=func, error=str(executor.stderr))
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def mail_alarm(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("mail alarm taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.BiosconfigSet()
        rsp.requestId = header[V2_REQUEST_ID]

        func = 'mail_alarm'
        self.execute_cmd(func, body)
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def snmp_alarm(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("snmp alarm taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.BiosconfigSet()
        rsp.requestId = header[V2_REQUEST_ID]

        func = 'snmp_alarm'
        self.execute_cmd(func, body)
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def performance_config(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("cpu performance taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.BiosconfigSet()
        rsp.requestId = header[V2_REQUEST_ID]

        func = 'performance_config'
        self.execute_cmd(func, body)
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def numa_config(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("numa config taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.BiosconfigSet()
        rsp.requestId = header[V2_REQUEST_ID]

        func = 'numa_config'
        self.execute_cmd(func, body)
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def get_sn(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("get bios info taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.BiosInfo()
        rsp.requestId = header[V2_REQUEST_ID]

        func = 'get_sn'
        cmd = "sh " + self.bios_set + func + " {} '{}' --ipaddr={}"
        executor = shell.call(cmd.format(body.username, body.password, body.ip))
        if executor.return_code != 0:
            raise exceptions.SetBiosV2Error(BmsCodeMsg.BIOS_ERROR, ip=body.ip, func=func, error=str(executor.stderr))
        output = executor.stdout.replace("\n", "")
        sysinfo = output.split(',')
        if len(sysinfo) != 3:
            raise exceptions.SetBiosV2Error(BmsCodeMsg.BIOS_ERROR, ip=body.ip, func=func,
                                            error="get sn/bios/bmc information failure")
        logger.debug("sn/bmc/bios result: %s" % output)
        rsp.data.update({"bios_version": sysinfo[0].replace(" ", "")})
        rsp.data.update({"bmc_version": sysinfo[1].replace(" ", "")})
        rsp.data.update({"SN": sysinfo[2].replace(" ", "")})
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def boot_set(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("set bios type taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.BiosconfigSet()
        rsp.requestId = header[V2_REQUEST_ID]

        func = 'boot_set'
        cmd = "sh " + self.bios_set + func + " {} '{}' --ipaddr={} --boot_type={}"
        boot_type = body.boot_type
        executor = shell.call(cmd.format(body.username, body.password, body.ip, boot_type.title()))
        if executor.return_code != 0:
            raise exceptions.SetBiosV2Error(BmsCodeMsg.BIOS_ERROR, ip=body.ip, func=func, error=str(executor.stderr))

        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def get_mac(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("get mac taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.BiosInfo()
        rsp.requestId = header[V2_REQUEST_ID]

        func = 'get_mac'
        cmd = "sh " + self.bios_set + func + " {} '{}' --ipaddr={}"
        executor = shell.call(cmd.format(body.username, body.password, body.ip))
        if executor.return_code != 0:
            raise exceptions.SetBiosV2Error(BmsCodeMsg.BIOS_ERROR, ip=body.ip, func=func, error=str(executor.stderr))
        output = executor.stdout.replace("\n", "")
        sysinfo = output.split(',')
        logger.debug("macs result: %s" % output)
        rsp.data.update({'macs': sysinfo})
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def pxe_config(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("pxe config taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.BiosconfigSet()
        rsp.requestId = header[V2_REQUEST_ID]

        func = 'pxe_config'
        cmd = "sh " + self.bios_set + func + " {} '{}' --ipaddr={} --pxe_device={}"
        executor = shell.call(cmd.format(body.username, body.password, body.ip, body.pxe_device))
        if executor.return_code != 0:
            raise exceptions.SetBiosV2Error(BmsCodeMsg.BIOS_ERROR, ip=body.ip, func=func, error=str(executor.stderr))

        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def boot_config(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("boot config taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.BiosconfigSet()
        rsp.requestId = header[V2_REQUEST_ID]

        func = 'boot_config'
        self.execute_cmd(func, body)

        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def config_raid(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("raid config taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.BiosconfigSet()
        rsp.requestId = header[V2_REQUEST_ID]

        func = 'config_raid'
        cmd = "sh " + self.bios_set + func + " {} '{}' --ipaddr={} --raid_type={} --disk_list={}"
        disk_list = ','.join(body.disk_list)
        executor = shell.call(cmd.format(body.username, body.password, body.ip, body.raid_type, disk_list))
        if executor.return_code != 0:
            raise exceptions.SetBiosV2Error(BmsCodeMsg.BIOS_ERROR, ip=body.ip, func=func, error=str(executor.stderr))

        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def set_alarm_and_cpu(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("set snmp ,cpu perforance/numa and timezone config taskuuid:%s body:%s" %
                    (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.BiosconfigSet()
        rsp.requestId = header[V2_REQUEST_ID]
        funcs = ['snmp_alarm', 'performance_config', 'numa_config', 'change_timezone']
        for func in funcs:
            self.execute_cmd(func, body)

        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def vnc_check(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("vnc console check taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.BiosconfigSet()
        rsp.requestId = header[V2_REQUEST_ID]

        func = 'vnc_control'
        cmd = "sh " + self.bios_set + func + " {} '{}' --ipaddr={}"
        executor = shell.call(cmd.format(body.username, body.password, body.ip))
        if executor.return_code != 0:
            raise exceptions.SetBiosV2Error(BmsCodeMsg.BIOS_ERROR, ip=body.ip, func=func, error=str(executor.stderr))

        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def sn_check(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("sn check taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.BiosconfigSet()
        rsp.requestId = header[V2_REQUEST_ID]

        func = 'single_sn'
        cmd = "sh " + self.bios_set + func + " {} '{}' --ipaddr={}"
        executor = shell.call(cmd.format(body.username, body.password, body.ip))
        if executor.return_code != 0:
            raise exceptions.SetBiosV2Error(BmsCodeMsg.BIOS_ERROR, ip=body.ip, func=func, error=str(executor.stderr))
        output = executor.stdout.replace("\n", "")
        logger.debug(output)
        if body.sn in executor.stdout:
            logger.debug("%s the record of sn is true" % body.ip)
        else:
            raise exceptions.SetBiosV2Error(BmsCodeMsg.BIOS_ERROR, ip=body.ip, func=func,
                                            error="The record of sn is false, actual result is %s" % output)

        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def bios_update(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("bios update taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.BiosconfigSet()
        rsp.requestId = header[V2_REQUEST_ID]

        func = 'bios_update'
        file_name = "".join([body.ip, "_", body.file.split('/')[-1]])
        file_path = ""
        if "http" not in body.file:
            file_path = os.path.dirname(body.file) + '/'
        cmd = "sh " + self.bios_set + func + " {} '{}' --ipaddr={} --update_file={} --is_restart={} --file_path={}"
        executor = shell.call(cmd.format(body.username, body.password, body.ip, file_name, body.restart_now, file_path))
        if executor.return_code != 0:
            raise exceptions.SetBiosV2Error(BmsCodeMsg.BIOS_ERROR, ip=body.ip, func=func, error=str(executor.stderr))
        output = executor.stdout.replace("\n", "")
        rsp.data = output.replace(" ", "")
        logger.debug(output)

        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def idrac_update(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("idrac update taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.BiosconfigSet()
        rsp.requestId = header[V2_REQUEST_ID]

        func = 'idrac_update'
        file_name = "".join([body.ip, "_", body.file.split('/')[-1]])
        file_path = ""
        if "http" not in body.file:
            file_path = os.path.dirname(body.file) + '/'
        cmd = "sh " + self.bios_set + func + " {} '{}' --ipaddr={} --update_file={} --file_path={}"
        executor = shell.call(cmd.format(body.username, body.password, body.ip, file_name, file_path))
        if executor.return_code != 0:
            raise exceptions.SetBiosV2Error(BmsCodeMsg.BIOS_ERROR, ip=body.ip, func=func, error=str(executor.stderr))
        output = executor.stdout.replace("\n", "")
        rsp.data = output.replace(" ", "")
        logger.debug(output)

        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def download_file(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("download update file taskuuid:%s, body: %s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.BiosconfigSet()
        rsp.requestId = header[V2_REQUEST_ID]

        if body.is_sure == "False":
            return jsonobject.dumps(rsp)
        file_name = "".join([body.ip, "_", body.url.split('/')[-1]])
        file_path = os.path.join(self.update_file, file_name)
        utils.prepare_pid_dir(file_path)
        file = requests.get(body.url, stream=True)

        if file.status_code != 200:
            raise exceptions.SetBiosV2Error(BmsCodeMsg.BIOS_ERROR, ip=body.ip, func=func,
                                            error="the status of Download address is not found")
        with open(file_path, 'wb') as fp:
            for i in file.iter_content(chunk_size=10240):
                fp.write(i)
        logger.debug("download file %s finish" % file_name)
        return jsonobject.dumps(rsp)



