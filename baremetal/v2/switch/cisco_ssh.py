import atexit
import contextlib
import logging
import random
import traceback

import re

import time
from netmiko.cisco import CiscoNxosSSH

from baremetal.common import locking as sw_lock, utils, jsonobject, http
import netmiko
import paramiko
from baremetal.common import exceptions
import tenacity
from oslo_config import cfg

# Internal ngs options will not be passed to driver.
from tooz import coordination

from baremetal.v2 import models
from baremetal.conductor.switch import cisco_ssh

logger = logging.getLogger(__name__)

CONF = cfg.CONF


class CiscoSwitch_v2(cisco_ssh.CiscoSwitch):

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
        except:
            logger.error(traceback.format_exc())
            raise
        return output
    def save_configuration(self, net_connect, cmd='copy running-config startup-config',):

        retry_kwargs = {'wait': tenacity.wait_random(min=2, max=6),
                        'reraise': False,
                        'stop': tenacity.stop_after_delay(30)}

        @tenacity.retry(**retry_kwargs)
        def _save():
            try:
                output = super(CiscoNxosSSH, net_connect).save_config()
                self._check_output(output, cmd)
            except Exception:
                raise
            return output

        return _save()

    @staticmethod
    def _check_output(output, commands):

        ERROR_MSG_PATTERNS = (re.compile(r'Error'),
                              re.compile(r'Incomplete'),
                              re.compile(r'Invalid'),
                              re.compile(r'Policy-map is being referenced'),
                              re.compile(r'Configuration update aborted'))

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
                    output = ""
                    self.send_config_set(net_connect, cmd_set)
                    try:
                        output = self.save_configuration(net_connect)
                    except tenacity.RetryError as ex:
                        logger.error("save configuration failed:%s" % ex)
                    return output
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
                    #output = self.save_configuration(net_connect)
                    return output
        except Exception:
            logger.error(traceback.format_exc())
        raise

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
        return self.my_send_config_set(commands)

    def unset_vlan(self, ports):
        cmds = self._unset_vlan(ports)
        commands = cmds + ['exit']
        logger.debug("unset vlan command:%s" % commands)
        return self.my_send_config_set(commands)

    def _unset_vlan(self, ports):
        commands = []
        for port in ports:
            if port.current_link_type == "trunk":
                commands += ["interface " + port.port_name,
                             "switchport",
                             "no switchport trunk allowed vlan",
                             "no switchport mode",
                             'no switchport', 'exit']
            else:
                commands += ["interface " + port.port_name,
                             "switchport",
                             "no switchport access vlan",
                             "no switchport mode",
                             "no switchport" ,"exit"]

        logger.debug("unset vlan command:%s" % commands)
        return commands

    def open_port(self, ports):
        open_cmd = []
        for port in ports:
            open_cmd += ["interface " + port, "no shutdown", "exit"]
        commands = open_cmd + ["exit"]
        logger.debug("open ports command:%s" % commands)
        return self.my_send_config_set(commands)

    def shutdown_port(self, ports):
        shutdown_cmd = []
        for port in ports:
            shutdown_cmd += ["interface " + port, "shutdown", "exit"]
        commands = shutdown_cmd + ["exit"]
        logger.debug("close ports command:%s" % commands)
        return self.my_send_config_set(commands)

    def create_limit_template(self, templates):
        create_command = []
        for template in templates:
            cir = int(template.bandwidth * 1024)
            qos_cmd = ["policy-map %s" % template.name, "class class-default",
                       "police cir %s kbps conform transmit violate drop" % cir,
                       "exit", "exit"]
            create_command += qos_cmd
        commands = create_command + ['exit']
        logger.debug("create template command:%s" % commands)
        return self.my_send_config_set(commands)

    def delete_limit_template(self, templates):
        delete_command = []
        for template in templates:
            undo_cmd = 'no policy-map ' + template
            delete_command += [undo_cmd]
        commands = delete_command + ['exit']
        logger.debug("delete template command:%s" % commands)
        return self.my_send_config_set(commands)

    def set_limit(self, limit_infos):
        inbound_cmd = []
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
        return self.my_send_config_set(commands)

    def unset_limit(self, limit_infos):
        inbound_cmd = []
        outbound_cmd = []
        for info in limit_infos:
            template_name = info.template_name
            inbound_cmd += ["interface " + info.inbound_port, "no service-policy input %s" % template_name, "exit"]
            outbound_cmd += ["interface " + info.outbound_port, "no service-policy output %s" % template_name, "exit"]

        commands = inbound_cmd + outbound_cmd + ["exit"]
        logger.debug("unset limit command:%s" % commands)
        return self.my_send_config_set(commands)


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
        return self.my_send_config_set(clean_cmd_set + init_dhclient_cmds)

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
        return self.my_send_config_set(clean_cmd_set + init_cmd_set)

    def _clean_all_config(self, switch, template_name=None):

        all_ports_cmd = []
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
        return self.my_send_config_set(clean_cmd_set)

    def get_relations(self, special_vlan=None, special_mac=[]):
        relations = []
        pattern = re.compile(r'\S+')
        if len(special_mac) > 0:
            for item in special_mac:
                datas = self.my_send_command("show mac address-table address %s | grep Eth" % item)
                for line in datas.split("\n"):
                    data = pattern.findall(line)
                    mac = ":".join(i[0:2] + ":" + i[2:4] for i in data[2].split("."))
                    relations.append({"mac": mac, "port": data[-1]})

        if special_vlan:
            datas = self.my_send_command("show mac address-table vlan %s | grep Eth" % special_vlan)
            for line in datas.split("\n"):
                data = pattern.findall(line)
                mac = ":".join(i[0:2] + ":" + i[2:4] for i in data[2].split("."))
                relations.append({"mac": mac, "port": data[-1]})

        return relations



class SwitchPlugin(object):

    @utils.replyerror
    def set_vlan(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        rsp = models.SetSwitchResponse()
        device_cfg = {
            "device_type": "cisco_nxos",
            "ip": body.host,
            "username": body.username,
            "password": body.password
        }
        with CiscoSwitch_v2(device_cfg) as client:
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
        device_cfg = {
            "device_type": "cisco_nxos",
            "ip": body.host,
            "username": body.username,
            "password": body.password
        }
        with CiscoSwitch_v2(device_cfg) as client:
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
        device_cfg = {
            "device_type": "cisco_nxos",
            "ip": body.host,
            "username": body.username,
            "password": body.password
        }
        with CiscoSwitch_v2(device_cfg) as client:
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
        device_cfg = {
            "device_type": "cisco_nxos",
            "ip": body.host,
            "username": body.username,
            "password": body.password
        }
        with CiscoSwitch_v2(device_cfg) as client:
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
        device_cfg = {
            "device_type": "cisco_nxos",
            "ip": body.host,
            "username": body.username,
            "password": body.password
        }
        with CiscoSwitch_v2(device_cfg) as client:
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
        device_cfg = {
            "device_type": "cisco_nxos",
            "ip": body.host,
            "username": body.username,
            "password": body.password
        }
        with CiscoSwitch_v2(device_cfg) as client:
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
        device_cfg = {
            "device_type": "cisco_nxos",
            "ip": body.host,
            "username": body.username,
            "password": body.password
        }
        with CiscoSwitch_v2(device_cfg) as client:
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
        device_cfg = {
            "device_type": "cisco_nxos",
            "ip": body.host,
            "username": body.username,
            "password": body.password
        }
        with CiscoSwitch_v2(device_cfg) as client:
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
            device_cfg = {
                "device_type": "cisco_nxos",
                "ip": switch.host,
                "username": switch.username,
                "password": switch.password
            }
            with CiscoSwitch_v2(device_cfg) as client:
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
            device_cfg = {
                "device_type": "cisco_nxos",
                "ip": switch.host,
                "username": switch.username,
                "password": switch.password
            }
            with CiscoSwitch_v2(device_cfg) as client:
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
        device_cfg = {
            "device_type": "cisco_nxos",
            "ip": body.host,
            "username": body.username,
            "password": body.password
        }
        relations = []
        with CiscoSwitch_v2(device_cfg) as client:
            vlan = int(body.vlan) if body.vlan else None
            macs = body.macs if body.macs else []
            try:
                relations = client.get_relations(special_vlan=vlan, special_mac=macs)
            except Exception as ex:
                raise exceptions.SwitchTaskError(error=str(ex))
        rsp.relations = relations
        return jsonobject.dumps(rsp)



    @utils.replyerror
    def save(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        rsp = models.AgentResponse()

        device_cfg = {
            "device_type": "cisco_nxos",
            "ip": body.host,
            "username": body.username,
            "password": body.password
        }
        with CiscoSwitch_v2(device_cfg) as client:
            try:
                result = client.save()
            except Exception as ex:
                raise exceptions.SwitchTaskError(error=str(ex))
            if "successfully" in result:
                logger.debug("switch %s save config successfully." % body.host)
            else:
                logger.error("switch %s save config config result: %s." %
                             (body.host, result))
        return jsonobject.dumps(rsp)


