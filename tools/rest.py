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


def init_image(req):
    path = '/baremetal/image/init'
    body = {
        "uuid": str(uuid.uuid4()),
        "hostname": "baremetal",
        "username": "root",
        "password": "cds-china",
        "root_ldev_id": "104",
        "networks": {
            "interfaces": [
                {
                    "id": "interface0",
                    "mac": "00:22:bd:19:c8:f3",
                    "ipaddr": "114.112.91.253",
                    "netmask": "255.255.255.248",
                    "gateway": "114.112.91.249"
                },
                {
                    "id": "interface1",
                    "mac": "00:08:9a:3a:3f:fc",
                    "ipaddr": None,
                    "netmask": None,
                    "gateway": None
                },
                {
                    "id": "interface2",
                    "mac": "00:13:71:af:49:51",
                    "ipaddr": None,
                    "netmask": None,
                    "gateway": None
                }
            ],
            "bonds": [
                {
                    "name": "bond0",
                    "mode": "4",
                    "bond": [
                        "interface1",
                        "interface2"
                    ],
                    "bond_miimon": 100,
                    "ipaddr": "2.2.2.2",
                    "mac": "00:13:71:af:49:51",
                    "netmask": "255.255.255.0",
                    "gateway": None
                }
            ],
            "dns": [
                "114.114.114.114",
                "114.114.115.115"
            ]
        }
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "init image result: %s" % result


def set_vlan(req):
    path = '/baremetal/switch/vlan/set'
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
    path = '/baremetal/switch/vlan/unset'
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


def set_limit(req):
    path = '/baremetal/switch/limit/set'
    body = {
        "username": sw_username,
        "password": sw_password,
        "host": sw_ip,
        "template_name": "12345678-100",
        "ports": ["10GE1/0/17", "10GE1/0/18"]
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "set limit result: %s" % result


def unset_limit(req):
    path = '/baremetal/switch/limit/unset'
    body = {
        "username": sw_username,
        "password": sw_password,
        "host": sw_ip,
        "template_name": "12345678-100",
        "ports": ["10GE1/0/11", "10GE1/0/12"]
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "unset limit result: %s" % result


def create_limit_template(req):
    path = '/baremetal/switch/limit/create'
    body = {
        "username": "admin123",
        "password": "CDS-china1",
        "host": "10.177.178.241",
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
    path = '/baremetal/switch/limit/delete'
    body = {
        "username": "admin123",
        "password": "CDS-china1",
        "host": "10.177.178.241",
        "templates": ["public", "private"]
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "delete limit template result: %s" % result


def change_passwd(req):
    path = '/baremetal/changepasswd'
    body = {
        "uuid": str(uuid.uuid4()),
        "root_ldev_id": "104",
        "username": "root",
        "password": "1q2w3e4r!"
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "change baremetal password result: %s" % result


def change_ip(req):
    path = '/baremetal/changeip'
    body = {
        "uuid": str(uuid.uuid4()),
        "root_ldev_id": "104",
        "networks": {
            "interfaces": [
                {
                    "id": "interface0",
                    "mac": "00:22:bd:19:c8:f3",
                    "ipaddr": "114.112.91.253",
                    "netmask": "255.255.255.248",
                    "gateway": "114.112.91.249"
                },
                {
                    "id": "interface1",
                    "mac": "00:08:9a:3a:3f:fc",
                    "ipaddr": None,
                    "netmask": None,
                    "gateway": None
                },
                {
                    "id": "interface2",
                    "mac": "00:13:71:af:49:51",
                    "ipaddr": None,
                    "netmask": None,
                    "gateway": None
                }
            ],
            "bonds": [
                {
                    "name": "bond0",
                    "mode": "4",
                    "bond": [
                        "interface1",
                        "interface2"
                    ],
                    "bond_miimon": 100,
                    "ipaddr": "2.2.2.2",
                    "mac": "00:13:71:af:49:51",
                    "netmask": "255.255.255.0",
                    "gateway": None
                }
            ],
            "dns": [
                "114.114.114.114",
                "114.114.115.115"
            ]
        }
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "change baremetal ip result: %s" % result


def ipmi_status(req):
    path = '/baremetal/ipmi/status'
    body = [
        {
            "ip": ip,
            "username": username,
            "password": password
        }
    ]
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "ipmi status result: %s" % result


def ipmi_stop(req):
    path = '/baremetal/ipmi/stop'
    body = [
        {
            "ip": ip,
            "username": username,
            "password": password
        }
    ]
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "ipmi stop result: %s" % result


def ipmi_start(req):
    path = '/baremetal/ipmi/start'
    body = [
        {
            "ip": ip,
            "username": username,
            "password": password,
            "mode": "uefi"
        }
    ]
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "ipmi start result: %s" % result


def get_lan1_mac(req):
    path = "/baremetal/ipmi/lan1mac"
    body = [
        {
            "ip": "10.177.180.16",
            "username": "usera",
            "password": "usera"
        },
        {
            "ip": "10.177.180.16",
            "username": "usera",
            "password": "usera"
        }
    ]
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "get_lan1_mac result: %s" % result


def host_scan(req):
    path = '/baremetal/host/scan'
    (status, result) = req.post(path, None, None)
    print simplejson.dumps(simplejson.loads(result), indent=4)


def disk_delete(req):
    path = '/baremetal/disk/delete'
    body = {
        "dev_id": "104"
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "disk delete result: %s" % result


def close_port(req):
    path = "/baremetal/port/close"
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
    path = "/baremetal/port/open"
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
    path = "/baremetal/switch/init"
    body = {
        "is_dhclient": True,
        "template_name": "12345678-1000",
        "switches": [
            {
                "username": sw_username,
                "password": sw_password,
                "host": sw_ip,
                "vlan_ids": ["1000", "1001", "2000-2005"],
                "ports": ["10GE1/0/11", "10GE1/0/12", "10GE1/0/13"]
            }
        ]
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "init all config result: %s" % result


def clean_all_config(req):
    path = "/baremetal/switch/clean"
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
    path = "/baremetal/switch/save"
    body = {
                "username": sw_username,
                "password": sw_password,
                "host": sw_ip
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "save switch result: %s" % result

def clone_image(req):
    path = "/baremetal/image/clone"
    body = {
        "src_ldev_id": "",
        "dest_ldev_id": ""
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "clone image result: %s" % result


def create_pxe_config(req):
    path = "/baremetal/pxeconfig/create"
    body = [
        {
            "instance_id": str(uuid.uuid4()),
            "mode": "bios",
            "mac": "6c:92:bf:62:c7:d6"
        },
        {
            "instance_id": str(uuid.uuid4()),
            "mode": "uefi",
            "mac": "6c:92:bf:62:c7:d7"
        }
    ]
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "create pxe config result: %s" % result


def delete_pxe_config(req):
    path = "/baremetal/pxeconfig/delete"
    body = [
        {
            "instance_id": str(uuid.uuid4()),
            "mode": "bios",
            "mac": "6c:92:bf:62:c7:d6"
        },
        {
            "instance_id": str(uuid.uuid4()),
            "mode": "uefi",
            "mac": "6c:92:bf:62:c7:d7"
        }
    ]
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "delete pxe config result: %s" % result


def get_relation_mac_and_port(req):
    path = "/baremetal/switch/relationship"
    body = {
        "username": sw_username,
        "password": sw_password,
        "host": sw_ip,
        "vlan": 2000,
        "mac": "6c:92:bf:62:c7:d6"
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "get relationship result: %s" % result


def ipmi_reset(req):
    path = '/baremetal/ipmi/reset'
    body = [
        {
            "ip": ip,
            "username": username,
            "password": password
        }
    ]
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "ipmi reset result: %s" % result

def start_serial_console(req):
    path = "/baremetal/serial/shellinabox/start"
    body = {
        "username": "admin",
        "password": "admin",
        "ip": "10.177.178.33",
        "port": "10000"
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "start serial console result: %s" % result

def stop_serial_console(req):
    path = "/baremetal/serial/shellinabox/stop"
    body = {
        "username": "admin",
        "password": "admin",
        "ip": "10.177.178.33"
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "start serial console result: %s" % result

def convert_custom_image(req):
    path = "/baremetal/image/convert"
    body = {
        "image_name": "aaaa"
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)

def check_image(req):
    path = "/baremetal/image/check"
    body = {
            "os_version": "centos7.6_test",
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)
    print "check_ipmi result: %s" % result


if __name__ == "__main__":
    ip = "10.177.178.86"
    username = "admin"
    password = "admin"
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
    # check_image(rest)
