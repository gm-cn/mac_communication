import logging
import os
import requests
import simplejson
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

    def execute_cmd(self, func, body, *args):
        cmd = ["sh", self.bios_set, func, body.username, "'{}'".format(body.password), "".join(["--ipaddr=", body.ip])]
        for arg in args:
            cmd.append(arg)

        executor = shell.call(' '.join(cmd))
        if executor.return_code != 0:
            raise exceptions.SetBiosV2Error(BmsCodeMsg.BIOS_ERROR, ip=body.ip, func=func, error=str(executor.stderr))
        return executor

    @staticmethod
    def file_param(ip, file):
        file_name = "".join([ip, "_", file.split('/')[-1]])
        file_path = ""
        if "http" not in file:
            file_path = os.path.dirname(body.file) + '/'
        return file_name, file_path

    @utils.replyerror_v2
    def add_bmc_user(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("add bmc user taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.BiosconfigSet()
        rsp.requestId = header[V2_REQUEST_ID]
        ip_info = jsonobject.loads(simplejson.dumps(
            {"username": body.adminname, "password": body.adminpassword, "ip": body.ip}))
        self.execute_cmd('add_bmc_user', ip_info, "--username={}".format(body.username),
                         "--userpassword='{}'".format(body.userpassword))
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def vnc_config(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("vnc config taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.BiosconfigSet()
        rsp.requestId = header[V2_REQUEST_ID]

        self.execute_cmd('vnc_config', body, "--vnc_password='{}'".format(body.vnc_password))
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def mail_alarm(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("mail alarm taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.BiosconfigSet()
        rsp.requestId = header[V2_REQUEST_ID]

        self.execute_cmd('mail_alarm', body)
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def snmp_alarm(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("snmp alarm taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.BiosconfigSet()
        rsp.requestId = header[V2_REQUEST_ID]

        self.execute_cmd('snmp_alarm', body)
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def performance_config(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("cpu performance taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.BiosconfigSet()
        rsp.requestId = header[V2_REQUEST_ID]

        self.execute_cmd('performance_config', body)
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def numa_config(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("numa config taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.BiosconfigSet()
        rsp.requestId = header[V2_REQUEST_ID]

        self.execute_cmd('numa_config', body)
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def get_sn(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("get bios info taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.BiosInfo()
        rsp.requestId = header[V2_REQUEST_ID]

        executor = self.execute_cmd('get_sn', body)
        output = executor.stdout.replace("\n", "")
        sysinfo = output.split(',')
        if len(sysinfo) != 3:
            raise exceptions.SetBiosV2Error(BmsCodeMsg.BIOS_ERROR, ip=body.ip, func='get_sn',
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

        self.execute_cmd('boot_set', body, "--boot_type={}".format(body.boot_type.title()))
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def get_mac(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("get mac taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.BiosInfo()
        rsp.requestId = header[V2_REQUEST_ID]

        executor = self.execute_cmd('get_mac', body)
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

        self.execute_cmd('pxe_config', body, "--pxe_device={}".format(body.pxe_device))
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def boot_config(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("boot config taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.BiosconfigSet()
        rsp.requestId = header[V2_REQUEST_ID]

        self.execute_cmd('boot_config', body)
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def config_raid(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("raid config taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.BiosconfigSet()
        rsp.requestId = header[V2_REQUEST_ID]

        self.execute_cmd('config_raid', body, "--raid_type={}".format(body.raid_type),
                         "--disk_list={}".format(','.join(body.disk_list)))
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

        self.execute_cmd('vnc_control', body)
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def sn_check(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("sn check taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.BiosconfigSet()
        rsp.requestId = header[V2_REQUEST_ID]

        executor = self.execute_cmd('single_sn', body)
        output = executor.stdout.replace("\n", "")
        logger.debug(output)
        if body.sn in executor.stdout:
            logger.debug("%s the record of sn is true" % body.ip)
        else:
            raise exceptions.SetBiosV2Error(BmsCodeMsg.BIOS_ERROR, ip=body.ip, func='single_sn',
                                            error="The record of sn is false, actual result is %s" % output)
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def bios_update(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("bios update taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.BiosconfigSet()
        rsp.requestId = header[V2_REQUEST_ID]

        file_name, file_path = self.file_param(body.ip, body.file)
        self.execute_cmd('bios_update', body, "--update_file={}".format(file_name),
                         "--is_restart={}".format(body.restart_now), "--file_path={}".format(file_path))

        logger.debug("get the version of bios")
        executor = self.execute_cmd('get_sn', body)
        output = executor.stdout.replace("\n", "").split(',')
        rsp.data = output[0].replace(" ", "")
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def idrac_update(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("idrac update taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.BiosconfigSet()
        rsp.requestId = header[V2_REQUEST_ID]

        file_name, file_path = self.file_param(body.ip, body.file)
        self.execute_cmd('idrac_update', body, "--update_file={}".format(file_name),
                         "--file_path={}".format(file_path))

        logger.debug("get the version of idrac")
        executor = self.execute_cmd('get_sn', body)
        output = executor.stdout.replace("\n", "").split(',')
        rsp.data = output[1].replace(" ", "")
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
