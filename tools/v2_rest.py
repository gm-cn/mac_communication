import httplib
import uuid

import simplejson

from baremetal.common import jsonobject

REST_SERVER = 'localhost'
REST_SERVER_PORT = 7081


class RestException(Exception):
    pass


class RestRequest(object):
    def __init__(self):
        self.host = REST_SERVER
        self.port = REST_SERVER_PORT
        self.callbackuri = 'http://%s:%s/debug/result' % (REST_SERVER,
                                                          REST_SERVER_PORT)
        self.headers = self._build_header()

    def _build_header(self):
        headers = {"Content-Type": "application/json",
                   "Accept": "application/json",
                   "taskuuid": str(uuid.uuid4()),
                   "callbackuri": self.callbackuri}
        return headers

    def _send_request(self, uri, method, body, token):
        if not uri:
            raise RestException("uri is required!")

        conn = None
        try:
            conn = httplib.HTTPConnection(self.host, self.port)
            if token:
                self.headers["Cookie"] = token
            conn.request(method, uri, body, self.headers)
            response = conn.getresponse()
            status = response.status
            result = response.read()
        except Exception, e:
            print "Exception: %s" % e
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


def set_vlan(req):
    path = '/v2/baremetal/switch/vlan/set'
    body = {
        "username": sw_username,
        "password": sw_password,
        "host": sw_ip,
        "ports": [
            {
                "port_name": "10GE2/0/5",
                "vlan_id": ["1800"],
                "current_link_type": "trunk",
                "set_link_type": "access"
            }
		]
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "set switch result: %s" % result


def unset_vlan(req):
    path = '/v2/baremetal/switch/vlan/unset'
    body = {
        "username": sw_username,
        "password": sw_password,
        "host": sw_ip,
        "ports": [
            {
                "port_name": "10GE1/0/13",
                "current_link_type": "access"
            }
        ]
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "unset vlan result: %s" % result



def create_limit_template(req):
    path = '/v2/baremetal/switch/limit/create'
    body = {
        "username": sw_username,
        "password": sw_password,
        "host": sw_ip,
        "templates": [
            {
                "name": "public",
                "bandwidth": 20
            },
            {
                "name": "private",
                "bandwidth": 100
            }
        ]
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "create limit template result: %s" % result


def delete_limit_template(req):
    path = '/v2/baremetal/switch/limit/delete'
    body = {
        "username": sw_username,
        "password": sw_password,
        "host": sw_ip,
        "templates": ["public", "private"]
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "delete limit template result: %s" % result

def ipmi_status(req):
    path = '/v2/baremetal/ipmi/status'
    body = {
            "ip": ip,
            "username": username,
            "password": password
        }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "ipmi status result: %s" % result


def ipmi_stop(req):
    path = '/v2/baremetal/ipmi/stop'
    body = {
            "ip": ip,
            "username": username,
            "password": password
        }

    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "ipmi stop result: %s" % result


def ipmi_start(req):
    path = '/v2/baremetal/ipmi/start'
    body = {
            "ip": ip,
            "username": username,
            "password": password,
            "mode": "uefi"
        }

    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "ipmi start result: %s" % result


def close_port(req):
    path = "/v2/baremetal/port/close"
    body = {
        "username": sw_username,
        "password": sw_password,
        "host": sw_ip,
        "ports": ["10GE1/0/11", "10GE1/0/12", "Eth-Trunk 5"]
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "close port result: %s" % result


def open_port(req):
    path = "/v2/baremetal/port/open"
    body = {
        "username": sw_username,
        "password": sw_password,
        "host": sw_ip,
        "ports": ["10GE1/0/11", "10GE1/0/12", "Eth-Trunk 5"]
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "open port result: %s" % result


def init_all_config(req):
    path = "/v2/baremetal/switch/init"
    body = {
        "is_dhclient": True,
        "template_name": "12345678-1000",
        "switches": [
            {
                "username": sw_username,
                "password": sw_password,
                "host": sw_ip,
                "vlan_ids": ["1000"],
                "ports": ["10GE1/0/11"]
            }
        ]
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "init all config result: %s" % result


def clean_all_config(req):
    path = "/v2/baremetal/switch/clean"
    body = {
        "template_name": "12345678-1000",
        "switches": [
            {
                "username": sw_username,
                "password": sw_password,
                "host": sw_ip,
                "ports": ["10GE1/0/11", "10GE1/0/12", "10GE1/0/13"]
            }
        ]
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "clean all config result: %s" % result

def save_switch(req):
    path = "/v2/baremetal/switch/save"
    body = {
                "username": sw_username,
                "password": sw_password,
                "host": sw_ip
    }

    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "save switch result: %s" % result

def get_relation_mac_and_port(req):
    path = "/v2/baremetal/switch/relationship"
    body = [{
        "username": sw_username,
        "password": sw_password,
        "host": sw_ip,
        "port": "10GE1/0/1"
    }]
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "get relationship result: %s" % result


def ipmi_reset(req):
    path = '/v2/baremetal/ipmi/reset'
    body = {
            "ip": ip,
            "username": username,
            "password": password
        }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "ipmi reset result: %s" % result

def add_bmc_user(req):
    path = '/v2/baremetal/ipmi/add_user'
    body = {
            "ip": ip,
            "adminname": adminname,
            "adminpassword": adminpassword,
            "username": username,
            "userpassword": password
        }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "add_bmc_user result: %s" % result

def vnc_config(req):
    path = '/v2/baremetal/ipmi/vnc'
    body = {
            "ip": ip,
            "username": username,
            "password": password,
            "vnc_password": vnc_password,
        }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "vnc_config result: %s" % result

def mail_alarm(req):
    path = '/v2/baremetal/ipmi/mail_alarm'
    body = {
            "ip": ip,
            "username": username,
            "password": password
        }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "mail_alarm result: %s" % result

def snmp_alarm(req):
    path = '/v2/baremetal/ipmi/snmp_alarm'
    body = {
            "ip": ip,
            "username": username,
            "password": password
        }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "snmp_alarm result: %s" % result

def cpu_pre(req):
    path = '/v2/baremetal/ipmi/performance'
    body = {
            "ip": ip,
            "username": username,
            "password": password
        }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "cpu_pre result: %s" % result

def numa_cpu(req):
    path = '/v2/baremetal/ipmi/numa'
    body = {
            "ip": ip,
            "username": username,
            "password": password
        }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "numa_cpu result: %s" % result

def get_sn(req):
    path = '/v2/baremetal/ipmi/info'
    body = {
            "ip": ip,
            "username": username,
            "password": password
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "get_sn result: %s" % result

def config_raid(req):
    path = '/v2/baremetal/ipmi/config_raid'
    body = {
            "ip": ip,
            "username": username,
            "password": password,
            "raid_type": "0",
            "disk_list": ["1.2"]
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "config_raid result: %s" % result

def hw_test(req):
    path = '/v2/baremetal/hardware_test'
    body = {
               "ip_list": ["ip1,ip2", "ip1,ip2"],
               "username": "root",
               "password": "cds-china",
               "log_id": "qwer"

    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "hw_test result: %s" % result

def set_boot(req):
    path = "/v2/baremetal/ipmi/boot_set"
    body = {
        "ip": ip,
        "username": username,
        "password": password,
    "boot_type": "Bios/Uefi"
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "set_boot result: %s" % result

def pxe_config(req):
    path = "/v2/baremetal/ipmi/nic_pxe"
    body = {
        "ip": ip,
        "username": username,
        "password": password,
    "pxe_device": "1,2,3"
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "pxe_config result: %s" % result

def boot_seq(req):
    path = "/v2/baremetal/ipmi/boot_seq"
    body = {
        "ip": ip,
        "username": username,
        "password": password
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "boot_seq result: %s" % result

def ping_host(req):
    path = "/v2/baremetal/ping"
    body = {
            "server_ip": ip
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "ping_host result: %s" % result

def check_ipmi(req):
    path = "/v2/baremetal/ipmi/check"
    body = {
            "ip": ip,
            "username": username,
            "password": password
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "check_ipmi result: %s" % result

def check_image(req):
    path = "/v2/baremetal/image/check"
    body = {
            "os_version": "centos7.6_test",
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "check_ipmi result: %s" % result

def crctest(req):
    path = "/v2/baremetal/crc_test"
    body = {
          "ip_list": ["10.100.100.251,10.100.100.252"],
               "username": "root",
               "password": "cds-china",
               "log_id": "qwer"
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print " result: %s" % result

def scp_hw_log(req):
    path = "/v2/baremetal/hw_log"
    body = {
            "log_id": "qwer"
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print " result: %s" % result

if __name__ == "__main__":
    ip = "10.177.178.86"
    username = "admin"
    password = "admin"
    adminname = "root"
    adminpassword = "calvin"
    vnc_password = "usera"
    sw_ip = "10.177.178.241"
    sw_username = "admin123"
    sw_password = "CDS-china1"

    rest = RestRequest()

    # create_limit_template(rest)
    # delete_limit_template(rest)
    # get_relation_mac_and_port(rest)
    # init_all_config(rest)
    # clean_all_config(rest)
    # open_port(rest)
    # close_port(rest)
    # set_vlan(rest)
    # unset_vlan(rest)
    # save_switch(rest)

    # set_vlan(rest)
    # ipmi_reset(rest)
    # ipmi_start(rest)
    # ipmi_status(rest)
    # ipmi_stop(rest)

    # add_bmc_user(rest)
    # vnc_config(rest)
    # mail_alarm(rest)
    # snmp_alarm(rest)
    # cpu_pre(rest)
    # numa_cpu(rest)
    # get_sn(rest)
    # config_raid(rest)
    # hw_test(rest)
    # pxe_config(rest)
    # boot_seq(rest)
    # set_boot(rest)
    # check_ipmi(rest)
    # check_image(rest)
    # crctest(rest)
    # scp_hw_log(rest)