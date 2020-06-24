import logging
import os

from baremetal.common import jsonobject, utils, http, exceptions, shell
from baremetal.conductor import models
from oslo_config import cfg
import subprocess, time

logger = logging.getLogger(__name__)
CONF = cfg.CONF


class ImagePlugin(object):
    def __init__(self):
        self.image_path = CONF.pxe.user_image_dir

    @utils.replyerror
    def checkout_image(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        logger.debug("image check body:%s" % req[http.REQUEST_BODY])
        rsp = models.AgentResponse()
        res = utils.check_image_exist(self.image_path, body.os_version)
        if not res:
            raise exceptions.ImageCheckError(os_version=body.os_version, error="The image template check failed")
        return jsonobject.dumps(rsp)

    @utils.replyerror
    def backup_image(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        logger.debug("image backup body:%s" % req[http.REQUEST_BODY])
        slave_mgr_ip = body.slave_mgr_ip
        image_path = body.tpl_path

        backup_cmd = 'scp %s %s:%s' % (image_path, slave_mgr_ip, image_path)
        executor = shell.call(backup_cmd)
        if executor.return_code != 0:
            raise exceptions.IPMIError(command=backup_cmd, error=str(executor.stderr))

        rsp = models.AgentResponse()
        return jsonobject.dumps(rsp)

    @utils.replyerror
    def transfer_image(self, req):
        """
        Shell command:
        rsync -avzP /tftpboot/user_images/test01.qcow2  rsync://10.240.122.2:873/data >> /tmp/$1".log"
        :param req:
        :return:
        """
        body = jsonobject.loads(req[http.REQUEST_BODY])
        logger.debug("image transfer body:%s" % body)

        transfer_ip = body.transferMgrIp
        local_file = body.tplPath + body.tplName
        log_file = "/tmp/{0}.log".format(body.workFlowId)
        remote_url = "rsync://{0}:{1}/data".format(transfer_ip, body.transferMgrPort)
        cmd = ["rsync", "-avP", local_file, remote_url, ">>", log_file]
        cmd = " ".join(cmd)
        logger.debug("rsync cmd: %s" % cmd)

        p = subprocess.Popen(cmd, stderr=subprocess.PIPE, shell=True)

        if p.poll() is not None:
            stderr = p.stderr.read()
            logger.debug("rsync cmd stderr: %s" % stderr)

            if stderr:
                rsp = models.AgentResponse(success=False, error=stderr)
                return jsonobject.dumps(rsp)

        taskuuid = req[http.REQUEST_HEADER]["Taskuuid"]
        headers = {http.TASK_UUID: taskuuid, "step": None}
        while True:
            extra = utils.query_task(body.workFlowId, p.pid)
            if (extra.get("status") == "failed"):
                rsp = models.AgentResponse(success=False, error="rsync process inner error")
                return jsonobject.dumps(rsp)

            http.json_post(body.processBackUrl, jsonobject.dumps(extra), headers)
            if (extra.get("progress") == "100"):
                break
            time.sleep(10)

        checksum_file = local_file + "_checksum"
        checksum_cmd = "rsync -avp %s %s" % (checksum_file, remote_url)
        logger.debug("rsync checksum cmd: %s" % checksum_cmd)
        executor = shell.call(checksum_cmd)
        if executor.return_code != 0:
            raise exceptions.IPMIError(command=checksum_cmd, error=str(executor.stderr))

        rsp = models.AgentResponse()
        return jsonobject.dumps(rsp)

    @utils.replyerror
    def delete_image(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        logger.debug("image delete body:%s" % req[http.REQUEST_BODY])
        tpl_name = body.image_name
        tpl_path = body.image_path

        tpl_full_path = os.path.join(tpl_path, tpl_name)
        tpl_checksum_full_path = os.path.join(tpl_path, tpl_name + '_checksum')
        creating_full_path = os.path.join(tpl_path, 'Creating_' + tpl_name)

        delete_cmd = 'rm -rf %s %s %s' % (tpl_full_path, tpl_checksum_full_path, creating_full_path)
        logger.debug("execute delete image cmd: %s" % delete_cmd)
        executor = shell.call(delete_cmd)
        if executor.return_code != 0:
            raise exceptions.IPMIError(command=delete_cmd, error=str(executor.stderr))

        rsp = models.AgentResponse()
        return jsonobject.dumps(rsp)
