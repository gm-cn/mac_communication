import logging
import random
import traceback

import re

import time
from netmiko.huawei import HuaweiSSH

from baremetal.common import locking as sw_lock, utils, jsonobject, http

from baremetal.common import exceptions
from baremetal.common.exceptions import BmsCodeMsg
import tenacity
from oslo_config import cfg

# Internal ngs options will not be passed to driver.

from baremetal.v2 import models
from baremetal.constants import V2_REQUEST_ID
from baremetal.conductor.switch import huawei_ssh

logger = logging.getLogger(__name__)

CONF = cfg.CONF


class HuaweiSwitch_v2(huawei_ssh.HuaweiSwitch):

    def send_config_set(self, net_connect, cmd_set):
        """Send a set of configuration lines to the device.

        :param net_connect: a netmiko connection object.
        :param cmd_set: a list of configuration lines to send.
        :returns: The output of the configuration commands.
        """
        try:
            net_connect.config_mode()
            output = net_connect.send_config_set(config_commands=cmd_set)
            self._check_output(output, cmd_set)
            logger.debug("\nresult:\n%s" % output)
        except:
            logger.error(traceback.format_exc())
            raise

    def send_command(self, net_connect, command):
        try:
            if command.startswith('dis'):
                net_connect.session_preparation()
            else:
                net_connect.config_mode()

            output = net_connect.send_command(command)
            self._check_output(output, command)
            logger.debug("\nresult:\n%s" % output)
            return output
        except:
            logger.error(traceback.format_exc())
            raise

    def save_configuration(self, net_connect, cmd='save',
                           confirm=True, confirm_response='Y'):

        retry_kwargs = {'wait': tenacity.wait_random(min=2, max=6),
                        'reraise': False,
                        'stop': tenacity.stop_after_delay(30)}

        @tenacity.retry(**retry_kwargs)
        def _save():
            try:
                output = super(HuaweiSSH, net_connect).save_config(
                    cmd=cmd,
                    confirm=confirm,
                    confirm_response=confirm_response)
                self._check_output(output, cmd)
            except Exception:
                raise
            return output

        return _save()

    @staticmethod
    def _check_output(output, commands):

        ERROR_MSG_PATTERNS = (re.compile(r'Error'),
                              re.compile(r'Wrong'),
                              re.compile(r'Incomplete'),
                              re.compile(r'Unrecognized'))

        if not output:
            return

        for pattern in ERROR_MSG_PATTERNS:
            if pattern.search(output):
                raise exceptions.ConfigSwitchError(
                    command=commands,
                    error=output)

        return output

    def my_send_config_set(self, cmd_set):
        if not cmd_set:
            logger.debug("Nothing to execute")
            return
        try:
            with sw_lock.PoolLock(self.locker, **self.lock_kwargs):
                with self._get_connection() as net_connect:
                    self.send_config_set(net_connect, cmd_set)
            return "successful"
        except Exception:
            logger.error(traceback.format_exc())
            raise

    def my_send_command(self, command):
        if not command:
            logger.debug("Nothing to execute")
            return
        try:
            with sw_lock.PoolLock(self.locker, **self.lock_kwargs):
                with self._get_connection() as net_connect:
                    output = self.send_command(net_connect, command)
                    return output
        except Exception:
            logger.error(traceback.format_exc())
            raise

    def save(self):
        with sw_lock.PoolLock(self.locker, **self.lock_kwargs):
            with self._get_connection() as net_connect:
                try:
                    output = self.save_configuration(net_connect)
                except tenacity.RetryError as ex:
                    logger.error("save configuration failed:%s" % ex)
                return output

    def gen_vlan_string(self, vlans):
        vlan_string = ""
        for vlan in vlans:
            if "-" in vlan:
                vlan = vlan.replace("-", " to ")
            vlan_string += str(vlan) + " "
        return vlan_string

    def set_vlan(self, ports):

        unset_vlan_cmd = self._unset_vlan(ports)

        set_vlan_cmd = []
        for port in ports:
            vlan_string = self.gen_vlan_string(port.vlan_id)
            if port.set_link_type == "trunk":
                set_vlan_cmd += ["interface " + port.port_name,
                                 "port link-type trunk",
                                 "port trunk allow-pass vlan %s" % vlan_string,
                                 "commit", "q"]
            else:
                set_vlan_cmd += ["interface " + port.port_name,
                                 "port link-type access",
                                 "port default vlan  %s" % vlan_string,
                                 "commit", "q"]
        commands = unset_vlan_cmd + set_vlan_cmd + ["q"]

        logger.debug("set vlan command:%s" % commands)
        return self.my_send_config_set(commands)

    def unset_vlan(self, ports):
        cmds = self._unset_vlan(ports)
        commands = cmds + ['q']
        logger.debug("unset vlan command:%s" % commands)
        return self.my_send_config_set(commands)

    def _unset_vlan(self, ports):
        commands = []
        unset_vlan_cmd = "undo port default vlan"
        for port in ports:
            if port.current_link_type == "trunk":
                commands += ["interface " + port.port_name,
                             'undo port link-type', 'commit', 'q']
            else:
                commands += ["interface " + port.port_name, 'undo port link-type',
                             unset_vlan_cmd, 'commit', 'q']

        logger.debug("unset vlan command:%s" % commands)
        return commands

    def set_limit(self, limit_infos):
        inbound_cmd = []
        outbound_cmd = []
        for info in limit_infos:
            template_name = info.template_name
            inbound_cmd += ["interface " + info.inbound_port,
                            "qos car inbound %s" % template_name, "commit", "q"]
            for port in info.outbound_ports:
                cir = int(info.bandwidth) * 1024
                cbs = min(524288, cir * 2)
                cmd1 = "qos lr cir %s kbps cbs %s kbytes outbound" % (cir, cbs)
                outbound_cmd += ["interface " + port, cmd1, "commit", "q"]

        commands = inbound_cmd + outbound_cmd + ['q']
        logger.debug("set limit command:%s" % commands)
        return self.my_send_config_set(commands)

    def unset_limit(self, inbound_ports, outbound_ports):
        inbound_cmd = []
        for port in inbound_ports:
            inbound_cmd += ["interface " + port, "undo qos car inbound", "commit", "q"]
        outbound_cmd = []
        for port in outbound_ports:
            outbound_cmd += ["interface " + port, "undo qos lr outbound", "commit", "q"]

        commands = inbound_cmd + outbound_cmd + ["q"]
        logger.debug("unset limit command:%s" % commands)
        return self.my_send_config_set(commands)

    def create_limit_template(self, templates):
        create_command = []
        for template in templates:
            cir = int(template.bandwidth * 1.62 * 1024)
            qos_cmd = "qos car %s cir %s kbps" % (template.name, cir)
            create_command += [qos_cmd, 'commit']
        commands = create_command + ['q']
        logger.debug("create template command:%s" % commands)
        return self.my_send_config_set(commands)

    def delete_limit_template(self, templates):
        delete_command = []
        for template in templates:
            undo_cmd = 'undo qos car ' + template
            delete_command += [undo_cmd, 'commit']
        commands = delete_command + ['q']
        logger.debug("delete template command:%s" % commands)
        return self.my_send_config_set(commands)

    def open_port(self, ports):
        open_cmd = []
        for port in ports:
            open_cmd += ["interface " + port, "undo shutdown", "commit", "q"]
        commands = open_cmd + ["q"]
        logger.debug("open ports command:%s" % commands)
        return self.my_send_config_set(commands)

    def shutdown_port(self, ports):
        shutdown_cmd = []
        for port in ports:
            shutdown_cmd += ["interface " + port, "shutdown", "commit", "q"]
        commands = shutdown_cmd + ["q"]
        logger.debug("close ports command:%s" % commands)
        return self.my_send_config_set(commands)

    def init_dhclient_config(self, switch, clean_cmd_set=[]):
        set_vlan_cmd = []
        if len(switch.vlan_ids) != 1:
            raise exceptions.ConfigInternalVlanError()

        for port in switch.ports:
            set_vlan_cmd += ["interface " + port,
                             "port link-type access",
                             "port default vlan %s" % switch.vlan_ids[0],
                             "q"]

        init_dhclient_cmds = set_vlan_cmd + ['commit', 'q']
        logger.debug("init dhclient ports command:%s" % init_dhclient_cmds)
        return self.my_send_config_set(clean_cmd_set + init_dhclient_cmds)

    def init_all_config(self, switch, template_name, is_dhclient):

        clean_cmd_set = self._clean_all_config(switch)

        if is_dhclient:
            return self.init_dhclient_config(switch, clean_cmd_set)

        all_ports_cmd = []
        # 1. create limit template
        bandwidth = int(template_name.split('-')[-1])
        cir = int(bandwidth * 1024)
        create_template_cmd = ["qos car %s cir %s kbps" % (template_name, cir), "commit"]

        vlan_string = ""
        for vlan in switch.vlan_ids:
            if "-" in vlan:
                vlan = vlan.replace("-", " to ")
            vlan_string += str(vlan) + " "

        # 2. set vlan
        for port in switch.ports:
            set_vlan_cmd = []
            set_vlan_cmd += ["interface " + port,
                             "port link-type trunk",
                             "port trunk allow-pass vlan %s" % vlan_string]

            # 3. set limit
            inbound_cmd = ["qos car inbound %s" % template_name]
            cir = int(bandwidth) * 1024
            cbs = min(524288, cir * 2)
            outbound_cmd = ["qos lr cir %s kbps cbs %s kbytes outbound" % (cir, cbs)]
            open_port_cmd = ["undo shutdown", "q"]

            port_per_cmd = set_vlan_cmd + inbound_cmd + outbound_cmd + open_port_cmd
            all_ports_cmd += port_per_cmd

        init_cmd_set = create_template_cmd + all_ports_cmd + ['commit', 'q']
        logger.debug("init config commands:%s" % init_cmd_set)
        if switch.vlan_ids:
            return self.my_send_config_set(clean_cmd_set + init_cmd_set)
        else:
            return "vlan information is null"

    def _clean_all_config(self, switch, template_name=None):

        all_ports_cmd = []
        delete_limit_template = []
        for port in switch.ports:
            # 1. unset vlan
            unset_vlan_cmd = ["interface " + port, "undo port link-type", "undo port default vlan"]

            # 2. unset limit
            unset_limit_cmd = ["undo qos car inbound", "undo qos lr outbound"]

            # 3. unset shutdown
            unset_shutdown_cmd = ["undo shutdown", "q"]

            port_per_cmd = unset_vlan_cmd + unset_limit_cmd + unset_shutdown_cmd
            all_ports_cmd += port_per_cmd

        # 3. delete limit template
        if template_name:
            delete_limit_template = ["undo qos car %s" % template_name]

        commands = all_ports_cmd + delete_limit_template
        logger.debug("clean config commands:%s" % commands)
        return commands

    def clean_all_config(self, switch, template_name=None):
        clean_cmd_set = self._clean_all_config(switch, template_name) + ['commit', 'q']
        return self.my_send_config_set(clean_cmd_set)

    def get_relations_port(self, port=None):
        pattern = re.compile(r'\w{4}-\w{4}-\w{4}')

        if port:
            command = "display mac-address interface %s" % port
            datas = self.my_send_command("display mac-address interface %s" % port)
            mac = ""
            for line in datas.split("\n"):
                data = pattern.findall(line)
                if data:
                    mac = ":".join(i[0:2] + ":" + i[2:4] for i in data[0].split("-")).upper()
                    break
            if mac == "":
                raise exceptions.ConfigSwitchV2Error(BmsCodeMsg.SWITCH_ERROR, command=command,
                                                     error="port-mac does not exist")
            return {"mac": mac, "port": port}


class SwitchPlugin(object):

    @utils.replyerror_v2
    def set_vlan(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]

        rsp = models.SetSwitchResponse()
        rsp.requestId = header[V2_REQUEST_ID]
        device_cfg = {
            "device_type": "huawei",
            "ip": body.host,
            "username": body.username,
            "password": body.password
        }
        with HuaweiSwitch_v2(device_cfg) as client:
            try:
                result = client.set_vlan(body.ports)
            except Exception as ex:
                raise exceptions.SwitchTaskV2Error(BmsCodeMsg.SWITCH_ERROR, error=str(ex))
            if "successfully" in result:
                for port in body.ports:
                    logger.debug("set vlan %s for port %s successfully."
                                 % (port.vlan_id, port.port_name))
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def unset_vlan(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]

        rsp = models.SetSwitchResponse()
        rsp.requestId = header[V2_REQUEST_ID]
        device_cfg = {
            "device_type": "huawei",
            "ip": body.host,
            "username": body.username,
            "password": body.password
        }
        with HuaweiSwitch_v2(device_cfg) as client:
            try:
                result = client.unset_vlan(body.ports)
            except Exception as ex:
                raise exceptions.SwitchTaskV2Error(BmsCodeMsg.SWITCH_ERROR, error=str(ex))
            if "successfully" in result:
                for port in body.ports:
                    logger.debug("unset vlan for port %s successfully."
                                 % ("Eth-Trunk %s" % port))
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def set_limit(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]

        rsp = models.SetSwitchResponse()
        rsp.requestId = header[V2_REQUEST_ID]
        device_cfg = {
            "device_type": "huawei",
            "ip": body.host,
            "username": body.username,
            "password": body.password
        }
        with HuaweiSwitch_v2(device_cfg) as client:
            try:
                result = client.set_limit(body.limit_infos)
            except Exception as ex:
                raise exceptions.SwitchTaskV2Error(BmsCodeMsg.SWITCH_ERROR, error=str(ex))
            if "successfully" in result:
                for info in body.limit_infos:
                    logger.debug("set limit for port %s successfully." % info.inbound_port)
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def unset_limit(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]

        rsp = models.SetSwitchResponse()
        rsp.requestId = header[V2_REQUEST_ID]
        device_cfg = {
            "device_type": "huawei",
            "ip": body.host,
            "username": body.username,
            "password": body.password
        }
        with HuaweiSwitch_v2(device_cfg) as client:
            try:
                result = client.unset_limit(body.inbound_ports, body.outbound_ports)
            except Exception as ex:
                raise exceptions.SwitchTaskV2Error(BmsCodeMsg.SWITCH_ERROR, error=str(ex))
            if "successfully" in result:
                for port in body.inbound_ports:
                    logger.debug("unset limit for port %s successfully." % port)
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def create_limit_template(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]

        rsp = models.SetSwitchResponse()
        rsp.requestId = header[V2_REQUEST_ID]
        device_cfg = {
            "device_type": "huawei",
            "ip": body.host,
            "username": body.username,
            "password": body.password
        }
        with HuaweiSwitch_v2(device_cfg) as client:
            try:
                result = client.create_limit_template(body.templates)
            except Exception as ex:
                raise exceptions.SwitchTaskV2Error(BmsCodeMsg.SWITCH_ERROR, error=str(ex))
            if "successfully" in result:
                for template in body.templates:
                    logger.debug("create limit template %s successfully."
                                 % template.name)
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def delete_limit_template(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]

        rsp = models.SetSwitchResponse()
        rsp.requestId = header[V2_REQUEST_ID]
        device_cfg = {
            "device_type": "huawei",
            "ip": body.host,
            "username": body.username,
            "password": body.password
        }
        with HuaweiSwitch_v2(device_cfg) as client:
            try:
                result = client.delete_limit_template(body.templates)
            except Exception as ex:
                raise exceptions.SwitchTaskV2Error(BmsCodeMsg.SWITCH_ERROR, error=str(ex))
            if "successfully" in result:
                for template in body.templates:
                    logger.debug("delete limit template %s successfully."
                                 % template)
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def open_port(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]

        rsp = models.SetSwitchResponse()
        rsp.requestId = header[V2_REQUEST_ID]
        device_cfg = {
            "device_type": "huawei",
            "ip": body.host,
            "username": body.username,
            "password": body.password
        }
        with HuaweiSwitch_v2(device_cfg) as client:
            try:
                result = client.open_port(body.ports)
            except Exception as ex:
                raise exceptions.SwitchTaskV2Error(BmsCodeMsg.SWITCH_ERROR, error=str(ex))
            if "successfully" in result:
                for port in body.ports:
                    logger.debug("open port %s successfully." % port)
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def close_port(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]

        rsp = models.SetSwitchResponse()
        rsp.requestId = header[V2_REQUEST_ID]
        device_cfg = {
            "device_type": "huawei",
            "ip": body.host,
            "username": body.username,
            "password": body.password
        }
        with HuaweiSwitch_v2(device_cfg) as client:
            try:
                result = client.shutdown_port(body.ports)
            except Exception as ex:
                raise exceptions.SwitchTaskV2Error(BmsCodeMsg.SWITCH_ERROR, error=str(ex))
            if "successfully" in result:
                for port in body.ports:
                    logger.debug("close port %s successfully." % port)
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def init_all_config(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]

        rsp = models.SetSwitchResponse()
        rsp.requestId = header[V2_REQUEST_ID]
        for switch in body.switches:
            device_cfg = {
                "device_type": "huawei",
                "ip": switch.host,
                "username": switch.username,
                "password": switch.password
            }
            with HuaweiSwitch_v2(device_cfg) as client:
                try:
                    time.sleep(random.randint(1, 3))
                    result = client.init_all_config(switch, body.template_name, body.is_dhclient)
                except Exception as ex:
                    raise exceptions.SwitchTaskV2Error(BmsCodeMsg.SWITCH_ERROR, error=str(ex))
                if "successfully" in result:
                    logger.debug("init switch %s port %s config successfully." %
                                 (switch.host, switch.ports))
                else:
                    logger.error("init switch %s port %s config result: %s." %
                                 (switch.host, switch.ports, result))
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def clean_all_config(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]

        rsp = models.SetSwitchResponse()
        rsp.requestId = header[V2_REQUEST_ID]
        for switch in body.switches:
            device_cfg = {
                "device_type": "huawei",
                "ip": switch.host,
                "username": switch.username,
                "password": switch.password
            }
            with HuaweiSwitch_v2(device_cfg) as client:
                try:
                    time.sleep(random.randint(1, 3))
                    result = client.clean_all_config(switch, body.template_name)
                except Exception as ex:
                    raise exceptions.SwitchTaskV2Error(BmsCodeMsg.SWITCH_ERROR, error=str(ex))
                if "successfully" in result:
                    logger.debug("clean switch %s port %s config successfully." %
                                 (switch.host, switch.ports))
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def get_relations(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]

        rsp = models.GetSwitchRelationsResp()
        rsp.requestId = header[V2_REQUEST_ID]

        relations = []
        for switch in body:
            device_cfg = {
                "device_type": "huawei",
                "ip": switch.host,
                "username": switch.username,
                "password": switch.password
            }
            with HuaweiSwitch_v2(device_cfg) as client:
                port = switch.port if switch.port else None
                try:
                    relation = client.get_relations_port(port=port)
                    relation.update({"ip": switch.host})
                except Exception as ex:
                    raise exceptions.SwitchTaskV2Error(BmsCodeMsg.SWITCH_ERROR, error=str(ex))
            relations.append(relation)
        rsp.data = relations
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def save(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]

        rsp = models.GetSwitchRelationsResp()
        rsp.requestId = header[V2_REQUEST_ID]

        device_cfg = {
            "device_type": "huawei",
            "ip": body.host,
            "username": body.username,
            "password": body.password
        }
        with HuaweiSwitch_v2(device_cfg) as client:
            try:
                result = client.save()
            except Exception as ex:
                raise exceptions.SwitchTaskV2Error(BmsCodeMsg.SWITCH_ERROR, error=str(ex))
            if "successfully" in result:
                logger.debug("switch %s save config successfully." % body.host)
            else:
                logger.error("switch %s save config config result: %s." %
                             (body.host, result))
        return jsonobject.dumps(rsp)
