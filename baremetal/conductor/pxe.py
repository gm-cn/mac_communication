import os

import logging
import pkg_resources
import shutil
import hashlib
from oslo_config import cfg

from baremetal.common import jsonobject, http, utils, shell, exceptions
from baremetal.conductor import models

logger = logging.getLogger(__name__)
CONF = cfg.CONF


class PxePlugin(object):
    def __init__(self):
        self.nfs_server_ip = CONF.pxe.nfs_server_ip
        self.tftpboot_dir = CONF.pxe.tftpboot_dir
        self.pxelinux_dir = CONF.pxe.pxelinux_dir
        self.deploy_image_dir = CONF.pxe.deploy_image_dir
        self.user_image_dir = CONF.pxe.user_image_dir
        self.instances_dir = os.path.join(self.pxelinux_dir, "instances")
        utils.mkdir(self.instances_dir)

    def copy_deploy_image(self, uuid, mac_file_name):
        instances_path = os.path.join(self.instances_dir, "%s" % uuid)
        utils.mkdir(instances_path)
        executor = shell.call("cp -rfd %s/* %s" % (self.deploy_image_dir, instances_path))
        if executor.return_code != 0:
            raise exceptions.MakeNfsrootError(mac=mac_file_name, error=executor.stderr)

    def gen_checksum(self, image_path):
        hash_value = hashlib.md5()
        with open(image_path, "rb") as f:
            maxbuf = 1024 * 1024  # bytes
            while True:
                buf = f.read(maxbuf)
                if not buf:
                    break
                hash_value.update(buf)
        return hash_value.hexdigest()


    def create_pxe_config(self, mac_file_name, uuid, deploy_mode):
        # 1. finish pxelinux.cfg/mac_file_name
        pxe_options = {}
        pxe_options["scheduler_callback"] = CONF.center.scheduler_callback
        pxe_options["user_image_path"] = "%s:%s" % (self.nfs_server_ip, self.user_image_dir)
        if deploy_mode == "bios":
            pxe_options["deploy_kernel"] = "instances/%s/deploy_kernel" % uuid
            pxe_options["deploy_ramdisk"] = "instances/%s/deploy_ramdisk" % uuid
            pxe_config_template = pkg_resources.resource_filename(
                'baremetal', "modules/pxe_bios_config.template")
            grub_dir = "%s/pxelinux.cfg" % self.pxelinux_dir
            utils.mkdir(grub_dir)
            pxe_config_file_path = os.path.join(grub_dir, "01-%s" % mac_file_name)
        elif deploy_mode == "uefi":
            pxe_options["deploy_kernel"] = "pxelinux/instances/%s/deploy_kernel" % uuid
            pxe_options["deploy_ramdisk"] = "pxelinux/instances/%s/deploy_ramdisk" % uuid
            pxe_config_template = pkg_resources.resource_filename(
                'baremetal', "modules/pxe_uefi_config.template")
            pxe_config_file_path = os.path.join(self.pxelinux_dir, "grub.cfg-01-%s" % mac_file_name)
        else:
            raise exceptions.UnsupportedMode(mode=deploy_mode)
        params = {"pxe_options": pxe_options}
        pxe_config = utils.render_template(pxe_config_template, params)
        with open(pxe_config_file_path, 'w') as f:
            f.write(pxe_config)

        self.copy_deploy_image(uuid, mac_file_name)

    @utils.replyerror
    def pxe_prepare(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        rsp = models.AgentResponse()

        for mac_boot in body:
            mac_file_name = mac_boot.mac.replace(":", "-").lower()
            self.create_pxe_config(mac_file_name, mac_boot.instance_id, mac_boot.mode)
            logger.debug("pxe prepare for baremetal:%s successfully." % mac_boot.mac)
        return jsonobject.dumps(rsp)

    @utils.replyerror
    def pxe_post(self, req):

        body = jsonobject.loads(req[http.REQUEST_BODY])
        rsp = models.AgentResponse()

        for mac_boot in body:
            delete_pxe_config = []
            mac_file_name = mac_boot.mac.replace(":", "-").lower()
            if mac_boot.mode == "bios":
                grub_dir = "%s/pxelinux.cfg" % self.pxelinux_dir
                pxe_bios_config_file_path = os.path.join(grub_dir, "01-%s" % mac_file_name)
                delete_pxe_config.append(pxe_bios_config_file_path)
            elif mac_boot.mode == "uefi":
                pxe_uefi_config_file_path = os.path.join(
                    self.pxelinux_dir, "grub.cfg-01-%s" % mac_file_name)
                delete_pxe_config.append(pxe_uefi_config_file_path)
            else:
                raise exceptions.UnsupportedMode(mode=mac_boot.mode)
            instance_path = os.path.join(self.instances_dir, "%s" % mac_boot.instance_id)
            delete_pxe_config.append(instance_path)

            for path in delete_pxe_config:
                try:
                    utils.remove_tree(path)
                except Exception as ex:
                    raise exceptions.DeletePxeConfigError(mac=mac_boot.mac, error=str(ex))
            logger.debug("delete pxe config for baremetal:%s successfully." % mac_boot.mac)
        return jsonobject.dumps(rsp)

    @utils.replyerror
    def test(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        rsp = models.AgentResponse()
        logger.debug("pxe boot test:%s successfully." %req[http.REQUEST_BODY])
        return jsonobject.dumps(rsp)

    @utils.replyerror
    def convert_image_format(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        rsp = models.ConvertCustomImage()

        custom_image_raw = os.path.join(self.user_image_dir, body.image_name)
        custom_image_partition = os.path.join(self.user_image_dir, '%s.partition' % body.image_name)
        custom_image_qcow2 = os.path.join(self.user_image_dir, '%s.qcow2' % body.image_name)
        rename_custom_image = os.path.join(self.user_image_dir, '%s_64' % body.image_name)

        executor = shell.call("sgdisk -l %s %s" % (custom_image_partition, custom_image_raw))
        logger.debug("partition table %s import custom image %s successful." %
                     (custom_image_partition, custom_image_raw))

        logger.debug("starting convert image format from %s to %s." % (custom_image_raw, custom_image_qcow2))
        executor = shell.call("qemu-img convert -t directsync -O qcow2 %s %s" %
                              (custom_image_raw, custom_image_qcow2))
        if executor.return_code != 0:
            logger.error(traceback.format_exc())
            raise exceptions.ConvertCustomImageError(src=custom_image_raw,
                                             dest=custom_image_qcow2,
                                             error=str(executor.stderr))
        shutil.move(custom_image_qcow2, rename_custom_image)
        checksum = self.gen_checksum(rename_custom_image)

        with open("%s_checksum" % rename_custom_image, 'w') as fp:
            fp.write(checksum)
        logger.debug("generate checksum  %s successful." % ("%s_checksum" % rename_custom_image))

        os.remove(custom_image_raw)
        os.remove(custom_image_partition)
        logger.debug("Image format conversion completed, remove image in raw format %s and partition %s."%
                     (custom_image_raw, custom_image_partition))

        rsp.custom_image_name = '%s_64' % body.image_name
        return jsonobject.dumps(rsp)