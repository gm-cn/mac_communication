import httplib
import uuid
import os
import sys
import simplejson
import time

REST_SERVER = '10.177.178.184'
REST_SERVER_PORT = 7070

def read_file(f_name):
    with open(f_name, "r") as fp:
        return fp.readline()

def checkout(task):
    if os.path.exists("/tmp/callback"):
        os.remove("/tmp/callback")

    while True:
        if os.path.exists("/tmp/callback"):
            time.sleep(1)
            callback = read_file("/tmp/callback")
            if "failed" in callback:
                print("%s failed" % task)
                p_id = read_file("/tmp/pidfile")
                os.system("kill %s" % p_id)
                sys.exit()
            print("%s finish" % task)
            break

class RestException(Exception):
    pass

class RestRequest(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.callbackuri = 'http://%s:%s/task/callback' % (REST_SERVER,
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
    (status, result) = req.post(path, data, None)

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
    (status, result) = req.post(path, data, None)

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
    (status, result) = req.post(path, data, None)

def start_serial_console(req, ipmi_ip, username, password):
    path = "/baremetal/serial/shellinabox/start"
    body = {
        "username": username,
        "password": password,
        "ip": ipmi_ip,
        "port": "10010"
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)

def stop_serial_console(req, ipmi_ip, username, password):
    path = "/baremetal/serial/shellinabox/stop"
    body = {
        "username": username,
        "password": password,
        "ip": ipmi_ip
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)

def init_image(req, mac, ip):
    path = '/pxe/baremetal/image/init'
    body = {
        "uuid": str(uuid.uuid4()),
        "hostname": "baremetal",
        "username": "root",
        "password": "cds-china",
        "os_type": "centos7",
        "enable_monitor": True,
        "networks": {
            "interfaces": [
                {
                    "mac": mac,
                    "ipaddr": ip,
                    "netmask": "255.255.255.0",
                    "dns": ["114.114.114.114", "114.114.115.115"]
                }
            ],
            "bonds": [
            ],
            "vlans": [
            ],
            "dns": [
                "114.114.114.114",
                "114.114.115.115"
            ]
        }
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)

def clone_image(req):
    path = '/pxe/baremetal/image/clone'
    body = {
        "os_version": "centos7.6_64"
    }
    data = simplejson.dumps(body)
    (status, result) = req.post(path, data, None)

if __name__ == "__main__":
    rest = RestRequest("localhost", "7081")

    try:
        res_s = os.system("python /root/bms_api/tools/notify.py &")

        username = "admin"
        password = "admin"
        ip = "10.177.178.86"
        mode = "uefi"

        if os.path.exists("/tmp/notify"):
            os.remove("/tmp/notify")
        if os.path.exists("/tmp/callback"):
            os.remove("/tmp/callback")

        # service power off
        ipmi_stop(rest, ip, username, password)
        checkout("service power off")
        time.sleep(2)

        # service power on from pxe
        ipmi_start(rest, ip, username, password, mode)
        # get dhcpIP from client service
        checkout("service power on from pxe")

        ip_mac = ''
        print("starting service for pxe")
        while True:
            if os.path.exists("/tmp/notify"):
                print("service boot finish")
                ip_mac = read_file("/tmp/notify")
                break
        mac = ip_mac.split(" ")[0]
        ipaddress = ip_mac.split(" ")[1]
        time.sleep(3)
        # create connection with pxeagent
        rest_pxe = RestRequest(ipaddress, "80")
        clone_image(rest_pxe)

        # start clone image, get callback
        checkout("clone image")

        # start init image
        init_image(rest_pxe, mac, ipaddress)
        checkout("init image")
        time.sleep(1)

        # reset service
        ipmi_reset(rest, ip, username, password)
        checkout("starting service for disk")


    except:
        pass
    finally:
        p_id = read_file("/tmp/pidfile")
        os.remove("/tmp/pidfile")
        os.system("kill %s" % p_id)
