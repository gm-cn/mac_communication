# coding=utf-8
import base64
import gzip
import json
import os
import posixpath
import shutil
import tempfile

import logging
import uuid

import simplejson
from oslo_config import cfg
from oslo_serialization import jsonutils

from baremetal.common import jsonobject, utils, http, exceptions, shell
from baremetal.common.utils import error_capture
from baremetal.conductor import configdrive, models
from baremetal.conductor.disks import DiskConfiguration

logger = logging.getLogger(__name__)

VERSION = "version"
CONTENT = "content"
CONTENT_DIR = "content"
MD_JSON_NAME = "meta_data.json"
VD_JSON_NAME = "vendor_data.json"
NW_JSON_NAME = "network_data.json"
UD_NAME = "user_data"

CONF = cfg.CONF


class RouteConfiguration(object):
    """Routes metadata paths to request handlers."""

    def __init__(self, path_handler):
        self.path_handlers = path_handler

    def handle_path(self, path_tokens):
        if len(path_tokens) == 1:
            path = VERSION
        else:
            path = '/'.join(path_tokens[1:])

        path_handler = self.path_handlers[path]

        if path_handler is None:
            raise KeyError(path)

        return path_handler()


class NetworkMetadata(object):
    def __init__(self, uuid, network_info):
        self.uuid = uuid
        self.network_info = network_info

    def _get_links(self, networks):
        links = []

        for iface in networks.interfaces:
            link = {
                'id': iface.id,
                'ethernet_mac_address': iface.mac,
                'type': "phy"
            }
            links.append(link)

        for group in networks.bonds:
            bond = {
                "id": group.name,
                "type": "bond",
                "ethernet_mac_address": group.mac,
                "bond_mode": group.mode,
                "bond_links": group.bond,
                "bond_miimon": group.bond_miimon
            }

            links.append(bond)
        return links

    def _get_networks(self, networks):
        nets = []
        for iface in networks.interfaces:
            if iface.ipaddr:
                network = {
                    "type": "ipv4",
                    "link": iface.id,
                    "ip_address": iface.ipaddr,
                    "netmask": iface.netmask
                }
                if iface.gateway:
                    network.update({"gateway": iface.gateway})
                nets.append(network)

        for group in networks.bonds:
            if group.ipaddr:
                network = {
                    "ip_address": group.ipaddr,
                    "link": group.name,
                    "netmask": group.netmask,
                    "type": "ipv4"
                }
                if group.gateway:
                    network.update({"gateway": group.gateway})
                nets.append(network)
        return nets

    def get_network_metadata(self):
        network_meta = self.network_info
        links = self._get_links(network_meta)
        networks = self._get_networks(network_meta)
        services = [{"address": dns, "type": "dns"} for dns in network_meta.dns]
        network_data = {
            "links": links,
            "networks": networks,
            "services": services
        }
        logger.debug("network_data for baremetal[uuid:%s]:%s" % (self.uuid, network_data))
        return network_data


class BaremetalMetadata(object):
    def __init__(self, baremetal, contents=None, network_info=None):

        self.uuid = baremetal.uuid
        self.username = baremetal.username
        self.hostname = baremetal.hostname
        self.password = baremetal.password

        user_data = '#cloud-config\nssh_pwauth: true\n' \
                    'disable_root: 0\nuser: %s\npassword: %s\n' \
                    'chpasswd:\n  expire: false' % (self.username, self.password)

        self.user_data = user_data

        self.files = []
        self.content = {}
        self.network_info = network_info

        if not contents:
            contents = []

        for (path, content) in contents:
            key = "%04i" % len(self.content)
            self.files.append({"path": path, "content_path": "/%s/%s" % (CONTENT_DIR, key)})

    def _metadata_to_json(self):
        metadata = {"uuid": self.uuid, 'hostname': self.hostname}
        if self.files:
            metadata['files'] = self.files
        logger.debug("metadata for baremetal[uuid:%s]:%s" % (self.uuid, metadata))
        return jsonutils.dump_as_bytes(metadata)

    def _user_data(self):

        return self.user_data

    def _vendor_data(self):
        return jsonutils.dump_as_bytes({})

    def _get_network_metadata(self):

        network_meta = NetworkMetadata(self.uuid, self.network_info)
        network_data = network_meta.get_network_metadata()
        return jsonutils.dump_as_bytes(network_data)

    def _route_configuration(self):
        path_handlers = {
            UD_NAME: self._user_data,
            MD_JSON_NAME: self._metadata_to_json,
            NW_JSON_NAME: self._get_network_metadata,
            VD_JSON_NAME: self._vendor_data
        }
        self.route_configuration = RouteConfiguration(path_handlers)
        return self.route_configuration

    def lookup(self, path):
        if path == "" or path[0] != '/':
            path = posixpath.normpath("/" + path)
        else:
            path = posixpath.normpath(path)

        path_tokens = path.split('/')[1:]
        return self.get_item(path_tokens[1:])

    def get_item(self, path_tokens):
        if path_tokens[0] == "content":
            return self._handle_content(path_tokens)
        if path_tokens[0] == "latest":
            return self._route_configuration().handle_path(path_tokens)

    def _handle_content(self, path_tokens):
        return self.content[path_tokens[1]]

    def metadata_for_configdrive(self):

        version = "latest"

        path = 'openstack/%s/%s' % (version, MD_JSON_NAME)
        yield (path, self.lookup(path))

        path = 'openstack/%s/%s' % (version, UD_NAME)
        if self.user_data is not None:
            yield (path, self.lookup(path))

        path = 'openstack/%s/%s' % (version, NW_JSON_NAME)
        yield (path, self.lookup(path))

        path = 'openstack/%s/%s' % (version, VD_JSON_NAME)
        yield (path, self.lookup(path))

        for (cid, content) in self.content.items():
            yield ('%s/%s/%s' % ("openstack", CONTENT_DIR, cid), content)


class BaremetalPlugin(object):
    def __init__(self):
        self.disk_utils = DiskConfiguration()

    def generate_configdrive(self, baremetal, networks):

        logger.debug("starting generate configdrive for baremetal[uuid:%s]" % baremetal.uuid)

        baremetal_meta = BaremetalMetadata(baremetal, network_info=networks)

        with tempfile.NamedTemporaryFile() as uncompressed:
            with configdrive.ConfigDriveBuilder(metadata=baremetal_meta) as cdb:
                cdb.make_configdrive(uncompressed.name)

            with tempfile.NamedTemporaryFile() as compressed:
                with gzip.GzipFile(fileobj=compressed, mode='wb') as gzipped:
                    uncompressed.seek(0)
                    shutil.copyfileobj(uncompressed, gzipped)

                compressed.seek(0)
                return base64.b64encode(compressed.read())

    @utils.replyerror
    def health(self, req):
        rsp = models.AgentResponse("success")
        return jsonobject.dumps(rsp)

    @utils.replyerror
    def init_image(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        logger.debug("init_image body:%s" % req[http.REQUEST_BODY])
        rsp = models.InitImageResponse()
        baremetal = {
            "uuid": body.uuid,
            "hostname": body.hostname,
            "username": body.username,
            "password": body.password
        }
        baremetal = jsonobject.loads(simplejson.dumps(baremetal))
        root_volume = utils.get_volume_path(body.root_ldev_id)
        if root_volume:
            device = os.path.realpath(root_volume)
        else:
            raise exceptions.VolumeNotFound(dev_id=body.root_ldev_id)
        configdrive = self.generate_configdrive(baremetal, body.networks)
        if configdrive is not None:
            self.disk_utils.create_config_drive_partition(body.uuid, device, configdrive)
        logger.debug("init image for baremetal[uuid:%s] successfully." % body.uuid)
        return jsonobject.dumps(rsp)

    @utils.replyerror
    def change_passwd(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        rsp = models.AgentResponse()
        root_volume = utils.get_volume_path(body.root_ldev_id)
        if root_volume:
            device = os.path.realpath(root_volume)
        else:
            raise exceptions.VolumeNotFound(dev_id=body.root_ldev_id)
        config_part = self.disk_utils.get_labelled_partition(body.uuid, device)

        with utils.tempdir() as tmpdir:
            mounted = False
            try:
                utils.mount(config_part, tmpdir)
                mounted = True
                user_data = os.path.join("%s/openstack/latest" % tmpdir, "user_data")
                userdata = '#cloud-config\nssh_pwauth: true\n' \
                           'disable_root: 0\nuser: %s\npassword: %s\n' \
                           'chpasswd:\n  expire: false\n' \
                           'network:\n    config: disabled' % \
                           (body.username, body.password)
                meta_data = os.path.join("%s/openstack/latest" % tmpdir, "meta_data.json")
                metadata = {"uuid": str(uuid.uuid4())}
                with open(user_data, 'w') as f:
                    f.write(userdata)
                with open(meta_data, 'w') as f:
                    json.dump(metadata, f)
            finally:
                if mounted:
                    utils.umount(tmpdir)
        logger.debug("change password for baremetal[uuid:%s] successfully." % body.uuid)
        return jsonobject.dumps(rsp)

    @utils.replyerror
    def change_ip(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        rsp = models.AgentResponse()
        baremetal_id = body.uuid
        root_volume = utils.get_volume_path(body.root_ldev_id)
        if root_volume:
            device = os.path.realpath(root_volume)
        else:
            raise exceptions.VolumeNotFound(dev_id=body.root_ldev_id)
        config_part = self.disk_utils.get_labelled_partition(baremetal_id, device)
        with utils.tempdir() as tmpdir:
            mounted = False
            try:
                utils.mount(config_part, tmpdir)
                mounted = True

                user_data = os.path.join("%s/openstack/latest" % tmpdir, "user_data")
                with open(user_data, 'w') as f:
                    f.write("")
                meta_data = os.path.join("%s/openstack/latest" % tmpdir, "meta_data.json")
                metadata = {"uuid": str(uuid.uuid4())}
                with open(meta_data, 'w') as f:
                    json.dump(metadata, f)
                network_data = os.path.join("%s/openstack/latest" % tmpdir, "network_data.json")
                bm_metadata = NetworkMetadata(baremetal_id, body.networks)
                net_data = bm_metadata.get_network_metadata()
                with open(network_data, 'w') as f:
                    json.dump(net_data, f)
            finally:
                if mounted:
                    utils.umount(tmpdir)
        logger.debug("change ip for baremetal[uuid:%s] successfully." % baremetal_id)
        return jsonobject.dumps(rsp)

    def clone_image(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        rsp = models.AgentResponse()
        src_volume = utils.get_volume_path(body.src_ldev_id)
        dest_volume = utils.get_volume_path(body.dest_ldev_id)
        if src_volume:
            src_device = os.path.realpath(src_volume)
        else:
            raise exceptions.VolumeNotFound(dev_id=body.src_ldev_id)
        if dest_volume:
            dest_device = os.path.realpath(dest_volume)
        else:
            raise exceptions.VolumeNotFound(dev_id=body.dest_ldev_id)
        try:
            utils.dd(src_device, dest_device, 'bs=1M', 'oflag=direct')
        except Exception as ex:
            raise exceptions.CloneImageError(src=src_volume, dest=dest_volume, error=str(ex))
        return jsonobject.dumps(rsp)

    """
        获取网卡mac信息以及对应交换机端口信息
    """
    def get_host_mac_list(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        rsp = models.GetHostRealNicMacListResponse()
        racadmcmd_prefix = "/opt/dell/srvadmin/sbin/racadm -r {} -u {} -p '{}' --nocertwarn".format(body.serverIp,
                                                                                                   body.username,
                                                                                                    body.rootPassword)
        @utils.error_capture
        def _get_mac_list():
            sysinfo_executor = shell.call("%s nicstatistics" % racadmcmd_prefix)
            nic_mac_list = []
            if sysinfo_executor.return_code:
                raise Exception(sysinfo_executor.stderr)
            for i in str(sysinfo_executor.stdout).split("\n"):
                if "NIC" in i:
                    nic_mac_list.append(i.strip().split(" - ")[-1].strip())

            return {"nic_mac_list":nic_mac_list}

        mac_result = _get_mac_list()
        if mac_result.get("error"):
            rsp.success = "Failed"
            rsp.error = mac_result.get("error")
        else:
            rsp.success = "Success"
            rsp.data = mac_result.get("nic_mac_list")
        return jsonobject.dumps(rsp)








