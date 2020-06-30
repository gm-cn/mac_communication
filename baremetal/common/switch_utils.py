import re
import logging
from oslo_config import cfg

CONF = cfg.CONF
logger = logging.getLogger(__name__)

pattern = re.compile(r'\w{4}-\w{4}-\w{4}')

def first_command():
    conn_type = CONF.sw_conn.conn_type
    return [] if conn_type == "ssh" else ['system-view']


def gen_vlan_string(vlans):
    vlan_string = ""
    for vlan in vlans:
        if "-" in vlan:
            vlan = vlan.replace("-", " to ")
        vlan_string += str(vlan) + " "
    return vlan_string


def alter_vlan(port):

    unset_vlan_cmd = first_command()
    undo_vlan = "undo port default vlan"

    unset_vlan_cmd += ["interface " + port.port_name ,'undo port link-type',
                       undo_vlan, 'commit', 'q']

    logger.debug("unset vlan command:%s" % unset_vlan_cmd)

    set_vlan_cmd = []
    vlan_string = gen_vlan_string(port.vlan_id)
    if port.sw_type == "trunk":
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

    logger.debug("alter vlan command:%s" % commands)
    return commands

def unset_vlan(ports):
    commands = first_command()
    unset_vlan_cmd = "undo port default vlan"
    for port in ports:
        commands += ["interface " + port.port_name,'undo port link-type',
                         unset_vlan_cmd, 'commit', 'q']

    logger.debug("unset vlan command:%s" % commands)
    return commands

def set_vlan(ports):
    set_vlan_cmd = []
    for port in ports:
        vlan_string = gen_vlan_string(port.vlan_id)
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
    logger.debug("set vlan command:%s" % set_vlan_cmd)
    return set_vlan_cmd

def clean_all_config(switch, template_name=None):

    all_ports_cmd = first_command()
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


def init_all_config(switch, template_name):
    all_ports_cmd = []
    # 1. create limit template
    bandwidth = int(template_name.split('-')[-1])
    cir = int(bandwidth * 1024)
    create_template_cmd = ["qos car %s cir %s kbps" % (template_name, cir), "commit"]

    # 2. set vlan
    for port in switch.ports:
        set_vlan_cmd = []
        set_vlan_cmd += ["interface " + port,
                         "port link-type trunk",
                         "port trunk allow-pass vlan %s" % gen_vlan_string(switch.vlan_ids)]

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

    return init_cmd_set


def open_port(ports):
    open_cmd = first_command()
    for port in ports:
        open_cmd += ["interface " + port, "undo shutdown", "commit", "q"]
    commands = open_cmd + ["q"]
    logger.debug("open ports command:%s" % commands)
    return commands

def shutdown_port(ports):
    shutdown_cmd = ["system-view"]
    for port in ports:
        shutdown_cmd += ["interface " + port, "shutdown", "commit", "q"]
    commands = shutdown_cmd + ["q"]
    logger.debug("close ports command:%s" % commands)
    return commands


def create_limit_template(templates):
    create_command = first_command()
    for template in templates:
        cir = int(template.bandwidth * 1.62 * 1024)
        qos_cmd = "qos car %s cir %s kbps" % (template.name, cir)
        create_command += [qos_cmd, 'commit']
    commands = create_command + ['q']
    logger.debug("create template command:%s" % commands)
    return commands

def delete_limit_template(templates):
    delete_command = first_command()
    for template in templates:
        undo_cmd = 'undo qos car ' + template
        delete_command += [undo_cmd, 'commit']
    commands = delete_command + ['q']
    logger.debug("delete template command:%s" % commands)
    return commands

def set_limit(limit_infos):
    inbound_cmd = first_command()
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
    return commands

def unset_limit(inbound_ports, outbound_ports):
    inbound_cmd = first_command()
    for port in inbound_ports:
        inbound_cmd += ["interface " + port, "undo qos car inbound", "commit", "q"]
    outbound_cmd = []
    for port in outbound_ports:
        outbound_cmd += ["interface " + port, "undo qos lr outbound", "commit", "q"]

    commands = inbound_cmd + outbound_cmd + ["q"]
    logger.debug("unset limit command:%s" % commands)
    return commands

def get_relations_port(datas):
    mac = ""
    for line in datas.split("\n"):
        data = pattern.findall(line)
        if data:
            mac = ":".join(i[0:2] + ":" + i[2:4] for i in data[0].split("-")).upper()
            break
    return mac

