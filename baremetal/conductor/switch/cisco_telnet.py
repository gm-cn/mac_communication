import telnetlib
import time
import re
import random
import traceback
import tenacity
from baremetal.common import exceptions
import logging

from baremetal.common import locking as sw_lock, exceptions, utils, jsonobject, http
from baremetal.conductor import models
from oslo_config import cfg

from tooz import coordination

from baremetal.conductor import models

logger = logging.getLogger(__name__)

CONF = cfg.CONF

class CiscoSwitch(models.ModelBase):

    def __init__(self, username, password, host, port=23, timeout=60):
        super(CiscoSwitch, self).__init__()
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.timeout = timeout
        self.sw_internal_cfg = {
            "sw_telnet_connect_timeout": 60,
            "sw_telnet_connect_interval": 10,
            "sw_max_connections": CONF.sw_coordination.max_connections
        }

        self.locker = None
        self.session_id = None
        if CONF.sw_coordination.backend_url:
            self.locker = coordination.get_coordinator(
                CONF.sw_coordination.backend_url,
                ('switch-' + self.host).encode('ascii'))
            self.locker.start()
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
            raise exceptions.SwitchConnectionError(ip=self.host, error=e)
        except Exception as e:
            logger.error("Unexpected exception during telnet connection")
            logger.error(traceback.format_exc())
            raise exceptions.SwitchConnectionError(ip=self.host, error=e)

        # Now yield the connection to the caller.
        return net_connect

    def _execute(self, command):
        logger.debug("command:%s" % command)
        net_connect = None
        result = ""
        try:
            with sw_lock.PoolLock(self.locker, **self.lock_kwargs):
                net_connect = self._get_connection()

                net_connect.read_until("login:")
                net_connect.write((self.username + '\n').encode('utf-8'))
                net_connect.read_until('Password:')
                net_connect.write((self.password + '\n').encode('utf-8'))
                for i in command:
                    net_connect.write((i + '\n').encode('utf-8'))
                error_msg = net_connect.read_until("Invalid", timeout=2)
                logger.debug("execute command :%s" % error_msg)
                if "Invalid" in error_msg and "Policy-map is being referenced" in error_msg:
                    result = net_connect.read_very_eager()
                    logger.debug("execute command failed.error msg:%s" % result)
                    raise exceptions.ConfigSwitchError(command=command, error=result)

                result = self.save_configuration(net_connect)

                count = 0
                while count < 60:
                    result += net_connect.read_very_eager()
                    if 'Copy complete.' in result:
                        logger.debug("config switch end..")
                        break
                    else:
                        count += 1
                        time.sleep(1)
        finally:
            logger.debug("session close.")
            net_connect.close()

        return result

    def save_configuration(self, net_connect):

        retry_kwargs = {'wait': tenacity.wait_random(min=2, max=6),
                        'reraise': False,
                        'stop': tenacity.stop_after_delay(30)}

        @tenacity.retry(**retry_kwargs)
        def _save():
            try:
                net_connect.write(("copy running-config startup-config" + '\n').encode('utf-8'))
                error_msg = net_connect.read_until("Invalid", timeout=2)
                logger.debug("execute command :%s" % error_msg)
                if "Configuration update aborted" in error_msg:
                    result = net_connect.read_very_eager()
                    logger.debug("execute command failed.error msg:%s" % result)
                    raise exceptions.ConfigSwitchError(command="copy running-config startup-config", error=result)
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

                net_connect.read_until("login:")
                net_connect.write((self.username + '\n').encode('utf-8'))
                net_connect.read_until('Password:')
                net_connect.write((self.password + '\n').encode('utf-8'))
                for i in command:
                    net_connect.write((i + '\n').encode('utf-8'))
                result = net_connect.read_until("Invalid", timeout=2)
                logger.debug("execute command :%s" % result)
        finally:
            logger.debug("session close.")

            if "Invalid" in result:
                result = net_connect.read_very_eager()
                logger.debug("execute command failed.error msg:%s" % result)
                net_connect.close()
                raise exceptions.ConfigSwitchError(command=command, error=result)
            else:
                net_connect.close()
                return result

    def gen_vlan_string(self, vlans):
        vlan_string = ""
        for vlan in vlans:
            vlan_string += str(vlan) + ","
        return vlan_string[:-1]

    def set_vlan(self, ports):

        unset_vlan_cmd = self._unset_vlan(ports)

        set_vlan_cmd = []
        for port in ports:
            vlan_string = self.gen_vlan_string(port.vlan_id)
            if port.set_link_type == "trunk":
                set_vlan_cmd += ["interface " + port.port_name,
                                 "switchport",
                                 "switchport mode trunk",
                                 "switchport trunk allowed vlan %s" % vlan_string,
                                 "exit"]
            else:
                set_vlan_cmd += ["interface " + port.port_name,
                                 "switchport",
                                 "switchport mode access",
                                 "switchport access vlan  %s" % vlan_string,
                                 "exit"]
        commands = unset_vlan_cmd + set_vlan_cmd + ["exit"]

        logger.debug("set vlan command:%s" % commands)
        return self._execute(commands)

    def unset_vlan(self, ports):
        cmds = self._unset_vlan(ports)
        commands = cmds + ['exit']
        logger.debug("unset vlan command:%s" % commands)
        return self._execute(commands)

    def _unset_vlan(self, ports):
        commands = ["configure terminal"]
        for port in ports:
            if port.current_link_type == "trunk":
                commands += ["interface " + port.port_name,
                             "switchport",
                             "no switchport trunk allowed vlan",
                             "no switchport mode",
                             'no switchport', 'exit']
            else:
                commands += ["interface " + port.port_name, "switchport", 'no switchport access vlan',
                             "no switchport mode", 'no switchport' ,'exit']

        logger.debug("unset vlan command:%s" % commands)
        return commands

    def open_port(self, ports):
        open_cmd = ["configure terminal"]
        for port in ports:
            open_cmd += ["interface " + port, "no shutdown", "exit"]
        commands = open_cmd + ["exit"]
        logger.debug("open ports command:%s" % commands)
        return self._execute(commands)

    def shutdown_port(self, ports):
        shutdown_cmd = ["configure terminal"]
        for port in ports:
            shutdown_cmd += ["interface " + port, "shutdown", "exit"]
        commands = shutdown_cmd + ["exit"]
        logger.debug("close ports command:%s" % commands)
        return self._execute(commands)

    def create_limit_template(self, templates):
        create_command = ["configure terminal"]
        for template in templates:
            cir = int(template.bandwidth * 1024)
            qos_cmd = ["policy-map %s" % template.name, "class class-default",
                       "police cir %s kbps conform transmit violate drop" % cir,
                       "exit", "exit"]
            create_command += qos_cmd
        commands = create_command + ['exit']
        logger.debug("create template command:%s" % commands)
        return self._execute(commands)

    def delete_limit_template(self, templates):
        delete_command = ["configure terminal"]
        for template in templates:
            undo_cmd = 'no policy-map ' + template
            delete_command += [undo_cmd]
        commands = delete_command + ['exit']
        logger.debug("delete template command:%s" % commands)
        return self._execute(commands)

    def set_limit(self, limit_infos):
        inbound_cmd = ["configure terminal"]
        outbound_cmd = []
        for info in limit_infos:
            template_name = info.template_name
            inbound_cmd += ["interface " + info.inbound_port,
                            "service-policy input %s" % template_name, "exit"]
            for port in info.outbound_ports:
                #cir = int(info.bandwidth) * 1024
                #cbs = min(524288, cir * 2)
                cmd1 = "service-policy output %s" % template_name
                outbound_cmd += ["interface " + port, cmd1, "exit"]

        commands = inbound_cmd + outbound_cmd + ['exit']
        logger.debug("set limit command:%s" % commands)
        return self._execute(commands)

    def unset_limit(self, limit_infos):
        inbound_cmd = ["configure terminal"]
        outbound_cmd = []
        for info in limit_infos:
            template_name = info.template_name
            inbound_cmd += ["interface " + info.inbound_port, "no service-policy input %s" % template_name, "exit"]
            outbound_cmd += ["interface " + info.outbound_port, "no service-policy output %s" % template_name, "exit"]

        commands = inbound_cmd + outbound_cmd + ["exit"]
        logger.debug("unset limit command:%s" % commands)
        return self._execute(commands)


    def init_dhclient_config(self, switch, clean_cmd_set=[]):
        set_vlan_cmd = []
        if len(switch.vlan_ids) != 1:
            raise exceptions.ConfigInternalVlanError()

        for port in switch.ports:
            set_vlan_cmd += ["interface " + port,
                             "switchport",
                             "switchport mode access",
                             "switchport access vlan  %s" % switch.vlan_ids[0],
                             "exit"]

        init_dhclient_cmds = set_vlan_cmd + ['exit']
        logger.debug("init dhclient ports command:%s" % init_dhclient_cmds)
        return self._execute(clean_cmd_set + init_dhclient_cmds)

    def init_all_config(self, switch, template_name, is_dhclient):

        clean_cmd_set = self._clean_all_config(switch)

        if is_dhclient:
            return self.init_dhclient_config(switch, clean_cmd_set)

        all_ports_cmd = []
        # 1. create limit template
        bandwidth = int(template_name.split('-')[-1])
        cir = int(bandwidth * 1024)
        create_template_cmd = ["policy-map %s" % template_name, "class class-default",
                               "police cir %s kbps conform transmit violate drop" % cir,
                               "exit", "exit"]

        vlan_string = self.gen_vlan_string(switch.vlan_ids)

        # 2. set vlan
        for port in switch.ports:
            set_vlan_cmd = []
            set_vlan_cmd += ["interface " + port,
                             "switchport",
                             "switchport mode trunk",
                             "switchport trunk allowed vlan %s" % vlan_string
                             ]

            # 3. set limit
            inbound_cmd = ["service-policy input %s" % template_name]
            #cir = int(bandwidth) * 1024
            #cbs = min(524288, cir * 2)
            #outbound_cmd = ["qos lr cir %s kbps cbs %s kbytes outbound" % (cir, cbs)]
            outbound_cmd = ["service-policy output %s" % template_name]
            open_port_cmd = ["no shutdown", "exit"]

            port_per_cmd = set_vlan_cmd + inbound_cmd + outbound_cmd + open_port_cmd
            all_ports_cmd += port_per_cmd

        init_cmd_set = create_template_cmd + all_ports_cmd + ['exit']
        logger.debug("init config commands:%s" % init_cmd_set)
        return self._execute(clean_cmd_set + init_cmd_set)

    def _clean_all_config(self, switch, template_name=None):

        all_ports_cmd = ["configure terminal"]
        delete_limit_template = []
        unset_limit_cmd = []
        for port in switch.ports:
            # 1. unset vlan
            unset_vlan_cmd = ["interface " + port,
                             "switchport",
                             "no switchport access vlan",
                             "no switchport trunk allowed vlan",
                             "no switchport mode"
                             ]

            # 2. unset limit
            if template_name:
                unset_limit_cmd = ["no service-policy input %s" % template_name, "no service-policy output %s" % template_name]

            # 3. unset shutdown
            unset_shutdown_cmd = ["no shutdown", "no switchport", "exit"]

            port_per_cmd = unset_vlan_cmd + unset_limit_cmd + unset_shutdown_cmd
            all_ports_cmd += port_per_cmd

        # 3. delete limit template
        if template_name:
            delete_limit_template = ["no policy-map %s" % template_name]

        commands = all_ports_cmd + delete_limit_template
        logger.debug("clean config commands:%s" % commands)
        return commands

    def clean_all_config(self, switch, template_name=None):
        clean_cmd_set = self._clean_all_config(switch, template_name) + ['exit']
        return self._execute(clean_cmd_set)

    def get_relations(self, special_vlan=None, special_mac=[]):
        relations = []
        pattern = re.compile(r'\S+')
        if len(special_mac) > 0:
            for item in special_mac:
                datas = self._execute_relative(["show mac address-table address %s | grep Eth" % item])
                for line in datas.split("\n")[24:-1]:
                    # if line[0] == "*":
                    data = pattern.findall(line)
                    mac = ":".join(i[0:2] + ":" + i[2:4] for i in data[2].split("."))
                    relations.append({"mac": mac, "port": data[-1]})

        if special_vlan:
            datas = self._execute_relative(["show mac address-table vlan %s | grep Eth" % special_vlan])
            for line in datas.split("\n")[24:-1]:
                # if line[0] == "*":
                data = pattern.findall(line)
                mac = ":".join(i[0:2] + ":" + i[2:4] for i in data[2].split("."))
                relations.append({"mac": mac, "port": data[-1]})

        return relations

class SwitchPlugin(object):

    @utils.replyerror
    def set_vlan(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        rsp = models.SetSwitchResponse()

        with CiscoSwitch(body.username, body.password, body.host) as client:
            try:
                result = client.set_vlan(body.ports)
            except Exception as ex:
                raise exceptions.SwitchTaskError(error=str(ex))
            if "Copy complete." in result:
                for port in body.ports:
                    logger.debug("set vlan %s for port %s successfully."
                                 % (port.vlan_id, port.port_name))
        return jsonobject.dumps(rsp)

    @utils.replyerror
    def unset_vlan(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        rsp = models.SetSwitchResponse()

        with CiscoSwitch(body.username, body.password, body.host) as client:
            try:
                result = client.unset_vlan(body.ports)
            except Exception as ex:
                raise exceptions.SwitchTaskError(error=str(ex))
            if "Copy complete." in result:
                for port in body.ports:
                    logger.debug("unset vlan for port %s successfully."
                                 % ("Eth-Trunk %s" % port))
        return jsonobject.dumps(rsp)

    @utils.replyerror
    def open_port(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        rsp = models.AgentResponse()

        with CiscoSwitch(body.username, body.password, body.host) as client:
            try:
                result = client.open_port(body.ports)
            except Exception as ex:
                raise exceptions.SwitchTaskError(error=str(ex))
            if "Copy complete." in result:
                for port in body.ports:
                    logger.debug("open port %s successfully." % port)
        return jsonobject.dumps(rsp)

    @utils.replyerror
    def close_port(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        rsp = models.AgentResponse()

        with CiscoSwitch(body.username, body.password, body.host) as client:
            try:
                result = client.shutdown_port(body.ports)
            except Exception as ex:
                raise exceptions.SwitchTaskError(error=str(ex))
            if "Copy complete." in result:
                for port in body.ports:
                    logger.debug("close port %s successfully." % port)
        return jsonobject.dumps(rsp)

    @utils.replyerror
    def set_limit(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        rsp = models.SetSwitchResponse()

        with CiscoSwitch(body.username, body.password, body.host) as client:
            try:
                result = client.set_limit(body.limit_infos)
            except Exception as ex:
                raise exceptions.SwitchTaskError(error=str(ex))
            if "Copy complete." in result:
                for info in body.limit_infos:
                    logger.debug("set limit for port %s successfully." % info.inbound_port)
        return jsonobject.dumps(rsp)

    @utils.replyerror
    def unset_limit(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        rsp = models.SetSwitchResponse()

        with CiscoSwitch(body.username, body.password, body.host) as client:
            try:
                result = client.unset_limit(body.limit_infos)
            except Exception as ex:
                raise exceptions.SwitchTaskError(error=str(ex))
            if "Copy complete." in result:
                for info in body.limit_infos:
                    logger.debug("unset limit for port %s successfully." % info.inbound_port)
        return jsonobject.dumps(rsp)

    @utils.replyerror
    def create_limit_template(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        rsp = models.SetSwitchResponse()

        with CiscoSwitch(body.username, body.password, body.host) as client:
            try:
                result = client.create_limit_template(body.templates)
            except Exception as ex:
                raise exceptions.SwitchTaskError(error=str(ex))
            if "Copy complete." in result:
                for template in body.templates:
                    logger.debug("create limit template %s successfully."
                                 % template.name)
        return jsonobject.dumps(rsp)

    @utils.replyerror
    def delete_limit_template(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        rsp = models.SetSwitchResponse()

        with CiscoSwitch(body.username, body.password, body.host) as client:
            try:
                result = client.delete_limit_template(body.templates)
            except Exception as ex:
                raise exceptions.SwitchTaskError(error=str(ex))
            if "Copy complete." in result:
                for template in body.templates:
                    logger.debug("delete limit template %s successfully."
                                 % template)
        return jsonobject.dumps(rsp)

    @utils.replyerror
    def init_all_config(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        rsp = models.AgentResponse()
        for switch in body.switches:

            with CiscoSwitch(switch.username, switch.password, switch.host) as client:
                try:
                    time.sleep(random.randint(1, 3))
                    result = client.init_all_config(switch, body.template_name, body.is_dhclient)
                except Exception as ex:
                    raise exceptions.SwitchTaskError(error=str(ex))
                if "Copy complete." in result:
                    logger.debug("init switch %s port %s config successfully." %
                                 (switch.host, switch.ports))
                else:
                    logger.error("init switch %s port %s config result: %s." %
                                 (switch.host, switch.ports, result))
        return jsonobject.dumps(rsp)


    @utils.replyerror
    def clean_all_config(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        rsp = models.AgentResponse()
        for switch in body.switches:
            with CiscoSwitch(switch.username, switch.password, switch.host) as client:
                try:
                    time.sleep(random.randint(1, 3))
                    result = client.clean_all_config(switch, body.template_name)
                except Exception as ex:
                    raise exceptions.SwitchTaskError(error=str(ex))
                if "Copy complete." in result:
                    logger.debug("clean switch %s port %s config successfully." %
                                 (switch.host, switch.ports))
        return jsonobject.dumps(rsp)

    @utils.replyerror
    def get_relations(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        rsp = models.GetSwitchRelationsResp()

        relations = []
        with CiscoSwitch(body.username, body.password, body.host) as client:
            vlan = int(body.vlan) if body.vlan else None
            macs = body.macs if body.macs else []
            try:
                relations = client.get_relations(special_vlan=vlan, special_mac=macs)
            except Exception as ex:
                raise exceptions.SwitchTaskError(error=str(ex))
        rsp.relations = relations
        return jsonobject.dumps(rsp)
