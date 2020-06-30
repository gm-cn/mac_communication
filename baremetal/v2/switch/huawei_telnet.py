import telnetlib
import time
import re
import random
import traceback
import tenacity
import logging

from oslo_config import cfg
from tooz import coordination

from baremetal.common import locking as sw_lock, exceptions, utils, jsonobject, http, switch_utils
from baremetal.common.exceptions import BmsCodeMsg
from baremetal.v2 import models
from baremetal.constants import V2_REQUEST_ID


logger = logging.getLogger(__name__)

CONF = cfg.CONF


class HuaweiSwitch_v2(models.ModelBase):

    def __init__(self, username, password, host, port=23, timeout=120):
        super(HuaweiSwitch_v2, self).__init__()
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.timeout = timeout
        self.sw_internal_cfg = {
            "sw_telnet_connect_timeout": 120,
            "sw_telnet_connect_interval": 10,
            "sw_max_connections": CONF.sw_coordination.max_connections
        }

        self.locker = None
        self.session_id = None
        if CONF.sw_coordination.backend_url:
            self.locker = coordination.get_coordinator(
                CONF.sw_coordination.backend_url,
                ('switch-' + self.host).encode('ascii'))
            try:
                self.locker.start()
            except Exception as e:
                raise exceptions.SwitchConnectionV2Error(BmsCodeMsg.SWITCH_ERROR, ip=self.host, error=e)
            self.session_id = hex(self.locker._coord.client_id[0])
            logger.debug("zookeeper client connection[session_id:%s] opened." % self.session_id)

        self.lock_kwargs = {
            'locks_pool_size': int(self.sw_internal_cfg['sw_max_connections']),
            'locks_prefix': self.host,
            'timeout': CONF.sw_coordination.acquire_lock_timeout}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.locker:
            self.locker.stop()
            logger.debug("zookeeper client connection[session_id:%s] closed." % self.session_id)

    def _get_connection(self):
        """
        This function hides the complexities of gracefully handling retrying
        failed connection attempts.
        """
        retry_exc_types = (EOFError, IndexError)

        # Use tenacity to handle retrying.
        @tenacity.retry(
            # Log a message after each failed attempt.
            after=tenacity.after_log(logger, logging.DEBUG),
            # Reraise exceptions if our final attempt fails.
            reraise=True,
            # Retry on TELNET connection errors.
            retry=tenacity.retry_if_exception_type(retry_exc_types),
            # Stop after the configured timeout.
            stop=tenacity.stop_after_delay(
                int(self.sw_internal_cfg['sw_telnet_connect_timeout'])),
            # Wait for the configured interval between attempts.
            wait=tenacity.wait_fixed(
                int(self.sw_internal_cfg['sw_telnet_connect_interval'])),
        )
        def _create_connection():
            return telnetlib.Telnet(self.host, self.port, self.timeout)

        # First, create a connection.
        try:
            net_connect = _create_connection()
        except tenacity.RetryError as e:
            logger.error("Reached maximum telnet connection attempts, not retrying")
            raise exceptions.SwitchConnectionV2Error(BmsCodeMsg.SWITCH_ERROR, ip=self.host, error=e)
        except Exception as e:
            logger.error("Unexpected exception during telnet connection")
            logger.error(traceback.format_exc())
            raise exceptions.SwitchConnectionV2Error(BmsCodeMsg.SWITCH_ERROR, ip=self.host, error=e)

        # Now yield the connection to the caller.
        return net_connect

    def _execute(self, command):
        logger.debug("command:%s" % command)
        net_connect = None
        result = ""
        try:
            with sw_lock.PoolLock(self.locker, **self.lock_kwargs):
                net_connect = self._get_connection()

                net_connect.read_until("Username:")
                net_connect.write((self.username + '\n').encode('utf-8'))
                net_connect.read_until('Password:')
                net_connect.write((self.password + '\n').encode('utf-8'))
                for i in command:
                    net_connect.write((i + '\n').encode('utf-8'))

                net_connect.write(('display version  | include BIOS' + '\n').encode('utf-8'))
                count = 0
                while count < 10:
                    error_msg = net_connect.read_until("Error", timeout=5)
                    logger.debug("execute command :%s" % error_msg)
                    if "display version  | include BIOS" in error_msg:
                        logger.debug("config switch end..")
                        break
                    else:
                        count += 1

        finally:
            logger.debug("session close.")
            net_connect.close()

        return "successfully"

    def save_configuration(self, net_connect):

        retry_kwargs = {'wait': tenacity.wait_random(min=2, max=6),
                        'reraise': False,
                        'stop': tenacity.stop_after_delay(60)}

        @tenacity.retry(**retry_kwargs)
        def _save():
            try:
                net_connect.write(("save" + '\n').encode('utf-8'))
                net_connect.write(('y' + '\n').encode('utf-8'))
                error_msg = net_connect.read_until("Error", timeout=2)
                logger.debug("execute command :%s" % error_msg)
                if "Error" in error_msg:
                    result = net_connect.read_very_eager()
                    logger.debug("execute command failed.error msg:%s" % result)
                    raise exceptions.ConfigSwitchV2Error(BmsCodeMsg.SWITCH_ERROR, command='save', error=result)
            except Exception:
                raise
            return error_msg

        return _save()

    def _execute_relative(self, command):
        logger.debug("command:%s" % command)
        net_connect = None
        result = ""
        try:
            with sw_lock.PoolLock(self.locker, **self.lock_kwargs):
                net_connect = self._get_connection()

                net_connect.read_until("Username:")
                net_connect.write((self.username + '\n').encode('utf-8'))
                net_connect.read_until('Password:')
                net_connect.write((self.password + '\n').encode('utf-8'))
                for i in command:
                    net_connect.write((i + '\n').encode('utf-8'))
                result = net_connect.read_until("Error", timeout=5)
                logger.debug("execute command :%s" % result)
        finally:
            logger.debug("session close.")

            if "Error" in result:
                result = net_connect.read_very_eager()
                logger.debug("execute command failed.error msg:%s" % result)
                net_connect.close()
                raise exceptions.ConfigSwitchV2Error(BmsCodeMsg.SWITCH_ERROR, command=command, error=result)
            else:
                net_connect.close()
                return result

    def save(self):
        logger.debug("command: save")
        net_connect = None
        try:
            with sw_lock.PoolLock(self.locker, **self.lock_kwargs):
                net_connect = self._get_connection()

                net_connect.read_until("Username:")
                net_connect.write((self.username + '\n').encode('utf-8'))
                net_connect.read_until('Password:')
                net_connect.write((self.password + '\n').encode('utf-8'))

                result = self.save_configuration(net_connect)
                count = 0
                while count < 60:
                    result += net_connect.read_very_eager()
                    if 'Save the configuration successfully' in result:
                        logger.debug("config switch end..")
                        break
                    else:
                        count += 1
                        time.sleep(1)
        finally:
            logger.debug("session close.")
            net_connect.close()

        return result

    def gen_vlan_string(self, vlans):
        vlan_string = ""
        for vlan in vlans:
            if "-" in vlan:
                vlan = vlan.replace("-", " to ")
            vlan_string += str(vlan) + " "
        return vlan_string

    def set_vlan(self, ports):
        unset_vlan_cmd = switch_utils.unset_vlan(ports)
        set_vlan_cmd = switch_utils.set_vlan(ports)

        commands = unset_vlan_cmd + set_vlan_cmd + ["q"]

        logger.debug("set vlan command:%s" % commands)
        return self._execute(commands)

    def unset_vlan(self, ports):
        cmds = switch_utils.unset_vlan(ports)
        commands = cmds + ["q"]
        logger.debug("unset vlan command:%s" % commands)
        return self._execute(commands)

    def _unset_vlan(self, ports):
        commands = ['system-view']
        unset_vlan_cmd = "undo port default vlan"
        for port in ports:
            commands += ["interface " + port.port_name,'undo port link-type',
                             unset_vlan_cmd, 'commit', 'q']

        logger.debug("unset vlan command:%s" % commands)
        return commands

    def alter_vlan(self, port):
        commands = switch_utils.alter_vlan(port)
        return self._execute(commands)

    def _clean_all_config(self, switch, template_name=None):

        all_ports_cmd = ['system-view']
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
        return self._execute(clean_cmd_set)

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
        if switch.vlan_ids:
            return self._execute(clean_cmd_set + init_dhclient_cmds)
        else:
            return "vlan information is null"

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
            return self._execute(clean_cmd_set + init_cmd_set)
        else:
            return "vlan information is null"

    def open_port(self, ports):
        commands = switch_utils.open_port(ports)
        return self._execute(commands)

    def shutdown_port(self, ports):
        commands = switch_utils.shutdown_port(ports)
        return self._execute(commands)

    def create_limit_template(self, templates):
        commands = switch_utils.create_limit_template(templates)
        return self._execute(commands)

    def delete_limit_template(self, templates):
        commands = switch_utils.delete_limit_template(templates)
        return self._execute(commands)

    def set_limit(self, limit_infos):
        commands = switch_utils.set_limit(limit_infos)
        return self._execute(commands)

    def unset_limit(self, inbound_ports, outbound_ports):
        commands = switch_utils.unset_limit(inbound_ports, outbound_ports)
        return self._execute(commands)

    def get_relations_port(self, port=None):
        if port:
            command = "display mac-address interface %s" % port
            datas = self._execute_relative(["display mac-address interface %s" % port])
            mac = switch_utils.get_relations_port(datas)
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

        with HuaweiSwitch_v2(body.username, body.password, body.host) as client:
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

        with HuaweiSwitch_v2(body.username, body.password, body.host) as client:
            try:
                result = client.unset_vlan(body.ports)
            except Exception as ex:
                raise exceptions.SwitchTaskV2Error(BmsCodeMsg.SWITCH_ERROR, error=str(ex))
            if "successfully" in result:
                for port in body.ports:
                    logger.debug("unset vlan for port %s successfully."
                                 % ("PORT: %s" % port.port_name))
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def init_all_config(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]

        rsp = models.SetSwitchResponse()
        rsp.requestId = header[V2_REQUEST_ID]

        for switch in body.switches:
            with HuaweiSwitch_v2(switch.username, switch.password, switch.host) as client:
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
            with HuaweiSwitch_v2(switch.username, switch.password, switch.host) as client:
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
    def open_port(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]

        rsp = models.SetSwitchResponse()
        rsp.requestId = header[V2_REQUEST_ID]

        with HuaweiSwitch_v2(body.username, body.password, body.host) as client:
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

        with HuaweiSwitch_v2(body.username, body.password, body.host) as client:
            try:
                result = client.shutdown_port(body.ports)
            except Exception as ex:
                raise exceptions.SwitchTaskV2Error(BmsCodeMsg.SWITCH_ERROR, error=str(ex))
            if "successfully" in result:
                for port in body.ports:
                    logger.debug("close port %s successfully." % port)
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def create_limit_template(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]

        rsp = models.SetSwitchResponse()
        rsp.requestId = header[V2_REQUEST_ID]

        with HuaweiSwitch_v2(body.username, body.password, body.host) as client:
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

        with HuaweiSwitch_v2(body.username, body.password, body.host) as client:
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
    def set_limit(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]

        rsp = models.SetSwitchResponse()
        rsp.requestId = header[V2_REQUEST_ID]

        with HuaweiSwitch_v2(body.username, body.password, body.host) as client:
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

        with HuaweiSwitch_v2(body.username, body.password, body.host) as client:
            try:
                result = client.unset_limit(body.inbound_ports, body.outbound_ports)
            except Exception as ex:
                raise exceptions.SwitchTaskV2Error(BmsCodeMsg.SWITCH_ERROR, error=str(ex))
            if "successfully" in result:
                for port in body.inbound_ports:
                    logger.debug("unset limit for port %s successfully." % port)
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def get_relations(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]

        rsp = models.GetSwitchRelationsResp()
        rsp.requestId = header[V2_REQUEST_ID]
        relations = []
        for switch in body:
            with HuaweiSwitch_v2(switch.username, switch.password, switch.host) as client:
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

        rsp = models.AgentResponse()
        rsp.requestId = header[V2_REQUEST_ID]

        with HuaweiSwitch_v2(body.username, body.password, body.host) as client:
            try:
                time.sleep(random.randint(1, 3))
                result = client.save()
            except Exception as ex:
                raise exceptions.SwitchTaskV2Error(BmsCodeMsg.SWITCH_ERROR, error=str(ex))
            if "successfully" in result:
                logger.debug("switch %s save config successfully." % body.host)
            else:
                logger.error("switch %s save config config result: %s." %
                             (body.host, result))
        return jsonobject.dumps(rsp)

    @utils.replyerror_v2
    def alter_vlan(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]

        rsp = models.AgentResponse()
        rsp.requestId = header[V2_REQUEST_ID]

        with HuaweiSwitch_v2(body.username, body.password, body.host) as client:
            try:
                result = client.alter_vlan(body.port)
            except Exception as ex:
                raise exceptions.SwitchTaskV2Error(BmsCodeMsg.SWITCH_ERROR, error=str(ex))
            if "successfully" in result:
                logger.debug("switch %s save config successfully." % body.host)
            else:
                logger.error("switch %s save config config result: %s." %
                             (body.host, result))
        return jsonobject.dumps(rsp)

