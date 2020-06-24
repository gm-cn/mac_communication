from test_service import read_file, checkout, RestRequest
import os
import time
import simplejson

def close_port(req, username, password, host, switch):
    path = "/baremetal/port/close"

    if switch == "huawei":
        ports = ["10GE1/0/1"]
    else:
        ports = ["Ethernet1/1"]

    body = {
        "username": username,
        "password": password,
        "host": host,
        "ports": ports
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)

def open_port(req, username, password, host, switch):
    path = "/baremetal/port/open"

    if switch == "huawei":
        ports = ["10GE1/0/1"]
    else:
        ports = ["Ethernet1/1"]

    body = {
        "username": username,
        "password": password,
        "host": host,
        "ports": ports
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)

def init_all_config(req, username, password, host, switch):
    path = "/baremetal/switch/init"

    if switch == "huawei":
        ports = ["10GE1/0/20", "10GE1/0/23"]
    else:
        ports = ["Ethernet1/2", "Ethernet1/3"]

    body = {
        "is_dhclient": False,
        "template_name": "12345678-1000",
        "switches": [
            {
                "username": username,
                "password": password,
                "host": host,
                "vlan_ids": ["1000", "1001", "2000-2005"],
                "ports": ports
            }
        ]
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)

def clean_all_config(req, username, password, host, switch):
    path = "/baremetal/switch/clean"

    if switch == "huawei":
        ports = ["10GE1/0/20", "10GE1/0/23"]
    else:
        ports = ["Ethernet1/2", "Ethernet1/3"]

    body = {
        "template_name": "12345678-1000",
        "switches": [
            {
                "username": username,
                "password": password,
                "host": host,
                "ports": ports
            }
        ]
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)

def set_vlan(req, username, password, host, switch):
    path = '/baremetal/switch/vlan/set'

    if switch == "huawei":
        port = "10GE1/0/24"
    else:
        port = "Ethernet1/4"

    body = {
        "username": username,
        "password": password,
        "host": host,
        "ports": [
            {
                "port_name": port,
                "vlan_id": ["2222", "2225-2233"],
                "current_link_type": "trunk",
                "set_link_type": "trunk"
            }
        ]
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)

def unset_vlan(req, username, password, host, switch):
    path = '/baremetal/switch/vlan/unset'

    if switch == "huawei":
        port = "10GE1/0/24"
    else:
        port = "Ethernet1/4"

    body = {
        "username": username,
        "password": password,
        "host": host,
        "ports": [
            {
                "port_name": port,
                "current_link_type": "trunk"
            }
        ]
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)

def set_limit(req, username, password, host):
    path = '/baremetal/switch/limit/set'
    body = {
        "username": username,
        "password": password,
        "host": host,
        "limit_infos": [
             {
                 "inbound_port": "Ethernet1/1",
                 "template_name": "private",
                 "outbound_ports": ["Ethernet1/1"]
             }
         ]

    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)

def unset_limit(req, username, password, host):
    path = '/baremetal/switch/limit/unset'
    body = {
        "username": username,
        "password": password,
        "host": host,
        "limit_infos": [
             {
                 "inbound_port": "Ethernet1/1",
                 "template_name": "private",
                 "outbound_port": "Ethernet1/1"
             }
        ]

    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)

def create_limit_template(req, username, password, host):
    path = '/baremetal/switch/limit/create'
    body = {
        "username": username,
        "password": password,
        "host": host,
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

def delete_limit_template(req, username, password, host):
    path = '/baremetal/switch/limit/delete'
    body = {
        "username": username,
        "password": password,
        "host": host,
        "templates": ["public"]
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)

if __name__ == '__main__':
    rest = RestRequest("localhost", "7081")
    #start = time.time()
    try:
        res_s = os.system("python ./notify.py &")
        time.sleep(30)

        username = "admin123"
        password = "CDS-china1"
        host = "10.177.178.241"
        switch = "huawei"

        if os.path.exists("/tmp/callback"):
            os.remove("/tmp/callback")
        start = time.time()
        open_port(rest, username, password, host, switch)
        checkout("open port")

        set_vlan(rest, username, password, host, switch)
        checkout("set vlan")

        create_limit_template(rest, username, password, host)
        checkout("create limit template")

        init_all_config(rest, username, password, host, switch)
        checkout("init switch all config")

        if switch == "cisco":
            set_limit(rest, username, password, host)
            checkout("set limit")
        print("===============clean switch config===============")

        if switch == "cisco":
            unset_limit(rest, username, password, host)
            checkout("unset limit")

        delete_limit_template(rest, username, password, host)
        checkout("clean limit template")

        unset_vlan(rest, username, password, host, switch)
        checkout("unset vlan")

        #clean_all_config(rest, username, password, host, switch)
        #checkout("clean switch all config")

        close_port(rest, username, password, host, switch)
        checkout("close port")
        print(time.time()-start)
    except:
        pass
    finally:
        p_id = read_file("/tmp/pidfile")
        os.remove("/tmp/pidfile")
        os.system("kill %s" % p_id)
