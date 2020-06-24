# -*- coding:utf-8 -*-
import httplib
import uuid
import simplejson
import time
import os
import tenacity
from configparser import ConfigParser
from get_excel_info import Excel
from database import Database_test
import logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(process)d %(name)s.%(lineno)d %(message)s',
                    datefmt='[%Y-%m_%d %H:%M:%S]',
                    filename='create_bms.log',
                    filemode='a')
logger = logging.getLogger(__name__)

cp = ConfigParser()
cp.read("bms.ini")

ex = Excel()
userinfo = ex.get_userinfo()

REST_SERVER = cp.get("rest", "rest_service")
REST_SERVER_PORT = cp.get("rest", "rest_service_port")

USERNAME_IMG = cp.get('image', 'username')
PASSWORD_IMG = cp.get('image', 'password')
OS_VERSION = cp.get('image', 'os_version')

NETMASK = cp.get('image', 'netmask')
TIMEOUT = int(cp.get('image', 'deploy_image_timeout'))
PXE_VLAN = cp.get('network', 'pxe_vlan')
nic_count = int(cp.get('network', 'count'))

MODE = userinfo[u'BootMode']
USERNAME = userinfo[u'带外账号']
PASSWORD = userinfo[u'带外密码']
SW_USERNAME = userinfo[u'交换机用户名']
SW_PASSWORD = userinfo[u'交换机密码']

def read_file(f_name):
    with open(f_name, "r") as fp:
        return fp.readline()


def checkout(task, id, ip, time=TIMEOUT):
    @tenacity.retry(wait=tenacity.wait_fixed(2), stop=tenacity.stop_after_delay(time))
    def _checkout():
        with Database_test() as data_t:
            res = data_t.select_attr(task, id)
            if res == "0":
                raise
            else:
                return res

    res = _checkout()
    if res != "failed":
        logger.debug("%s execute task %s success" % (ip, task))
        print("%s execute task %s success" % (ip, task))
    else:
        logger.debug("%s execute task %s failed" % (ip, task))
        print("%s execute task %s failed" % (ip, task))
        raise

    return res

def checkout_gethardinfo(task, ip, time=TIMEOUT):
    @tenacity.retry(wait=tenacity.wait_fixed(2), stop=tenacity.stop_after_delay(time))
    def _checkout():
        with Database_test() as data_t:
            res = data_t.select_dhcp_ipmi(ip)
            if res:
                return res
            else:
                raise

    res = _checkout()
    if res[0] == ip:
        return res[1]
    else:
        raise Exception("%s get dhcp ip failed")


class RestException(Exception):
    pass


class RestRequest(object):
    def __init__(self, host, port, create_id):
        self.host = host
        self.port = port
        self.create_id = create_id
        self.callbackuri = 'http://%s:%s/task/callback' % (REST_SERVER,
                                                           REST_SERVER_PORT)
        self.headers = self._build_header()

    def _build_header(self):
        headers = {"Content-Type": "application/json",
                   "Accept": "application/json",
                   "taskuuid": self.create_id,
                   "callbackuri": self.callbackuri}
        return headers

    def _send_request(self, uri, method, body, token):
        if not uri:
            raise RestException("uri is required!")

        conn = None
        try:
            conn = httplib.HTTPConnection(self.host, self.port)
            if token:
                self.headers["step"] = token
            conn.request(method, uri, body, self.headers)
            response = conn.getresponse()
            status = response.status
            result = response.read()
        except Exception, e:
            print
            "Exception: %s" % e
            raise e
        finally:
            if conn:
                conn.close()

        return status, result

    def get(self, uri, body=None, token=None):
        return self._send_request(uri, "GET", body, token)

    def post(self, uri, body, token):
        return self._send_request(uri, "POST", body, token)

    def put(self, uri, body, token):
        return self._send_request(uri, "PUT", body, token)

    def delete(self, uri, body, token):
        return self._send_request(uri, "DELETE", body, token)


def ipmi_stop(req, ipmi_ip, username, password):
    path = '/baremetal/ipmi/stop'
    body = [
        {
            "ip": ipmi_ip,
            "username": username,
            "password": password
        }
    ]
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, "poweroff_s")


def ipmi_start(req, ipmi_ip, username, password, mode):
    path = '/baremetal/ipmi/start'
    body = [
        {
            "ip": ipmi_ip,
            "username": username,
            "password": password,
            "mode": mode
        }
    ]
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, "poweron_s")


def ipmi_reset(req, ipmi_ip, username, password):
    path = '/baremetal/ipmi/reset'
    body = [
        {
            "ip": ipmi_ip,
            "username": username,
            "password": password,
        }
    ]
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, "powerreset_s")


def init_image(req, hostname, interfaces=[], bonds=[]):
    path = '/pxe/baremetal/image/init'
    body = {
        "uuid": str(uuid.uuid4()),
        "hostname": hostname,
        "username": USERNAME_IMG,
        "mode": MODE,
        "password": PASSWORD_IMG,
        "os_type": 'centos7',
        "networks": {
            "interfaces": interfaces,
            "bonds": bonds,
            "vlans": [],
            "dns": [
                "114.114.114.114"
            ]
        }
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, "init_s")


def clone_image(req, os_version):
    path = '/pxe/baremetal/image/clone'
    body = {
        "os_version": os_version
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, "clone_s")

def set_vlan(req, ip ,ports):
    path = '/baremetal/switch/vlan/set'
    body = {
        "username": SW_USERNAME,
        "password": SW_PASSWORD,
        "host": ip,
        "ports": ports
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, 'set_vlan')

def unset_vlan(req, ip, ports):
    path = '/baremetal/switch/vlan/unset'
    body = {
        "username": SW_USERNAME,
        "password": SW_PASSWORD,
        "host": ip,
        "ports": ports
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, 'unset_vlan')

def get_hardware_info(req):
    hostinfo = []
    path = "/pxe/baremetal/hardwareinfo"
    (status, result) = req.get(path, None, "get_hwinfo_s")
    hardinfo = simplejson.loads(result)

    ip = hardinfo["bmc_address"]
    hostinfo.append(ip)
    macs = []
    for i in hardinfo["net_info"]:
        if i["has_carrier"] == True:
            macs.append(i["mac_address"].upper())
    macs.sort()
    hostinfo.extend(macs)
    with Database_test() as data_t:
        try:

            data_t.insert_host(hostinfo)
        except:
            pass

    if len(macs) == nic_count:
       logger.debug("get hardware information %s success" % hostinfo)
    else:
       logger.debug("get hardware information %s error" % hostinfo) 

    return hostinfo

def get_hardinfo(rest_pxe):
    ips = get_hardware_info(rest_pxe)
    return ips


def boot_deploy_image(*attr):
    create_uuid = str(uuid.uuid4())
    create_res = []

    username = USERNAME
    password = PASSWORD

    ip = attr[0]

    mode = MODE
    os_version = OS_VERSION

    with Database_test() as data_t:
        data_t.insert(create_uuid, ip)

    try:
        rest = RestRequest("localhost", "7081", create_uuid)
        ipmi_stop(rest, ip, username, password)
        print("%s execute task %s success" % (ip, "power off"))
        create_res.append(checkout("poweroff_s", create_uuid, ip))
        time.sleep(10)

        ipmi_start(rest, ip, username, password, mode)
        # get dhcpIP from client service
        print("%s execute task %s success" % (ip, "power on"))
        create_res.append(checkout("poweron_s", create_uuid, ip))

        try:
            print("%s starting service for pxe" % ip)
            logger.debug("%s starting service for pxe" % ip)
            ipaddress = checkout("dhcp_ip", create_uuid, ip)
            time.sleep(1)
        except:
            ipmi_start(rest, ip, username, password, mode)
            # get dhcpIP from client service
            print("%s execute task %s success" % (ip, "power on"))
            create_res.append(checkout("poweron_s", create_uuid, ip))
            print("%s starting service for pxe" % ip)
            logger.debug("%s starting service for pxe" % ip)
            ipaddress = checkout("dhcp_ip", create_uuid, ip)
            time.sleep(1)


        rest_pxe = RestRequest(ipaddress, "80", create_uuid)
        
        ips = get_hardinfo(rest_pxe)
        print("%s get hardware info success %s" % (ip, ipaddress))

        # start clone image, get callback
        print("%s starting clone image" % ip)
        logger.debug("%s starting clone image" % ip)
        clone_image(rest_pxe, os_version)
        create_res.append(checkout("clone_s", create_uuid, ip, time=1500))
        time.sleep(1)

        with Database_test() as data_t:
            res = data_t.select_host_conf(ip)
            dhcp_mac = data_t.select_createbms_info('dhcp_mac', ip)
            dhcp_mac = dhcp_mac[0].upper()

        hostname = res[-1]
        interfaces = []
        macs = list(ips[1:-1])
        if macs[0] != dhcp_mac:
            idx = macs.index(dhcp_mac)
            macs[0], macs[idx] = macs[idx], macs[0]
        host_ip = []
        for i in range(len(macs)):
            count = int(i + 1)
            a = {
                "mac": macs[i],
                "ipaddr": res[count],
                "netmask": NETMASK
            }
            host_ip.append(res[count])
            interfaces.append(a)
            
        print("%s starting clone init" % ip)
        init_image(rest_pxe, hostname, interfaces)
        create_res.append(checkout("init_s", create_uuid, ip))
        time.sleep(1)
    except:
        with Database_test() as data_t:
            data_t.update_host("failed", ip)
        raise

    with Database_test() as data_t:
        if "failed" in create_res:
            data_t.update_host("failed", ip)
            raise
        else:
            data_t.update_host("success", ip)
            now_path = os.getcwd()
            filepath1 = now_path + '/host_ip'
            with open(filepath1, 'a') as fp:
                str_host_ip = ' '.join(host_ip)
                fp.write(str_host_ip + '\n')


    # reset service
    ipmi_reset(rest, ip, username, password)
    checkout("powerreset_s", create_uuid, ip)

def pxe_set_vlan():
    create_uuid = "1234"
    rest = RestRequest("localhost", "7081", create_uuid)
    excel = Excel()
    res = excel.get_pxe_port()
    for i in res.keys():
        ip = i
        ports = []
        for j in res[i]:
            port = {
                "port_name": j,
                "vlan_id": [PXE_VLAN],
                "current_link_type": "access",
                "set_link_type": "access"
            }
            ports.append(port)
        logger.debug("switch:%s set port info:%s" % (ip, ports))
        if ports:
            set_vlan(rest, ip, ports)
        time.sleep(5)

def other_set_vlan(num):
    create_uuid = "1234"
    rest = RestRequest("localhost", "7081", create_uuid)
    excel = Excel()
    res = excel.get_other_suc_port(num)
    for i in res.keys():
        ip = i
        ports = []
        for j in res[i]:
            port = {
                "port_name": j,
                "vlan_id": [PXE_VLAN],
                "current_link_type": "access",
                "set_link_type": "access"
            }
            ports.append(port)
        logger.debug("switch:%s set port info:%s" % (ip, ports))
        if ports:
            set_vlan(rest, ip, ports)
        time.sleep(10)

def pxe_unset_vlan():
    create_uuid = "1234"
    rest = RestRequest("localhost", "7081", create_uuid)
    excel = Excel()
    res = excel.get_all_port()
    for i in res.keys():
        ip = i
        ports = []
        for j in res[i]:
            port = {
                "port_name": j,
                "current_link_type": "access"
            }
            ports.append(port)
        logger.debug("switch:%s set port info:%s" % (ip, ports))
        if ports:
            unset_vlan(rest, ip, ports)
        time.sleep(10)
