import os

import signal
import simplejson
import subprocess
import time
import psutil
import logging
import pkg_resources
from oslo_config import cfg

from baremetal.common import jsonobject, http, utils, shell, exceptions
from baremetal.conductor import models
from baremetal.conductor.ipmi import IPMIPlugin
logger = logging.getLogger(__name__)
CONF = cfg.CONF

class SerialConsolePlugin(object):
    def __init__(self):
        self.serial_pid_dir = CONF.shellinabox_console.pid_dir
        self.manager_ip = CONF.shellinabox_console.host_ip
        self.subprocess_timeout = int(CONF.shellinabox_console.subprocess_timeout)
        self.ipmi = IPMIPlugin()

    def get_serial_pid(self, pidfile):
        pid = None
        pid_context = None
        if os.path.exists(pidfile):
            with open(pidfile, 'r') as fp:
                pid_context = fp.readline()
        if pid_context:
            pid = int(pid_context.strip())
        return pid

    def get_shellinabox_console_url(self, ip, port):
        url = "%s://%s:%s" % ("http", ip, port)
        logger.debug("host serial console url:%s" % (url))
        return url

    def _start_shellinabox_console(self, client, port, pidfile):
        self._stop_shellinabox_console(client, pidfile)

        ipmi_cmd = self.ipmi.start_sol_console_cmd(client)
        utils.mkdir(self.serial_pid_dir)

        shellinabox_cmd = 'shellinaboxd -t -p %s --background=%s ' \
                          '--css=/usr/share/shellinabox/white-on-black.css -s /:%s:%s:HOME:"%s"' \
                          % (port, pidfile, os.getuid(), os.getgid(), ipmi_cmd)
        logger.debug("start host:%s serial console cmd %s" % (client.ip, shellinabox_cmd))
        return shellinabox_cmd

    def _stop_shellinabox_console(self, client, pidfile):
        if os.path.exists(pidfile):
            pid = self.get_serial_pid(pidfile)
            if pid and psutil.pid_exists(pid):
                os.kill(pid, signal.SIGTERM)

                attempt = 0
                max_attempt = 5
                while attempt < max_attempt:
                    if psutil.pid_exists(pid):
                        if attempt == max_attempt -1:
                            os.kill(pid, signal.SIGKILL)
                        logger.debug("Waiting host %s for the console process exit." % (client.ip))
                        attempt += 1
                        time.sleep(0.2)
                    else:
                        break

            os.remove(pidfile)
            ipmi_cmd = self.ipmi.stop_sol_console_cmd(client)
            executor = shell.call(ipmi_cmd)
            logger.debug("host %s console process exit, delete pid file %s" % (client.ip, pidfile))
        else:
            logger.debug("No console pid found for host %s while trying to stop shellinabox console." % client.ip)

    @utils.replyerror
    def start_shellinabox_console(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        logger.debug("host scan body:%s" % req[http.REQUEST_BODY])

        pidfile = os.path.join(self.serial_pid_dir, "host-%s.pid" % body.ip.replace('.', '_'))

        rsp = models.SerialConsoleOpenResponse()
        client_info = {
            "ip": body.ip,
            "username": body.username,
            "password": body.password
        }
        client_info = jsonobject.loads(simplejson.dumps(client_info))
        start_cmd = self._start_shellinabox_console(client_info, body.port, pidfile)
        try:
            executor = subprocess.Popen(start_cmd,
                                        shell=True,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
        except (OSError, ValueError) as e:
            logger.warning("host %s start serial console failed.Error msg:%s" % (body.ip, str(e)))
            raise exceptions.StartSerialConsole(ip=body.ip, error=str(e))

        logger.debug("host serial console exec:%s" % executor.poll())
        locals = {"return_code": None, "err": ''}
        timeout = time.time() + self.subprocess_timeout
        while True:
            locals["return_code"] = executor.poll()
            pid = self.get_serial_pid(pidfile)
            if (locals["return_code"] == 0 and os.path.exists(pidfile)
                    and psutil.pid_exists(pid)):
                logger.debug("host %s serial console cmd returncode:%s" % (body.ip, locals["return_code"]))
                logger.debug("host %s serial console pid file:%s, PID:%s" % (body.ip, pidfile, pid))
                logger.debug("host %s serial console start successful" % (body.ip))
                break

            if (time.time() > timeout
                    or locals["return_code"] is not None):
                err = ''
                if locals["return_code"] != 0:
                    (stdout, stderr) = executor.communicate()
                    err = stderr
                else:
                    self._stop_shellinabox_console(client_info, pidfile)

                err_str = "Timeout or error while waiting for console, ERROR:" + str(err)
                logger.warning("host %s start serial console failed.Error msg:%s" % (body.ip, err_str))
                locals["err"] = err_str
                break

            logger.debug("host %s serial console cmd returncode:%s  PID:%s   running:%s"
                         % (body.ip, locals["return_code"], pid, psutil.pid_exists(pid)))
            time.sleep(0.02)

        if locals["err"]:
            logger.warning("host %s start serial console failed.Error msg:%s" % (body.ip, locals["err"]))
            raise exceptions.StartSerialConsole(ip=body.ip, error=locals["err"])

        rsp.url = self.get_shellinabox_console_url(self.manager_ip, body.port)
        return jsonobject.dumps(rsp)

    @utils.replyerror
    def stop_shellinabox_console(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        logger.debug("host scan body:%s" % req[http.REQUEST_BODY])
        rsp = models.AgentResponse()
        client_info = {
            "ip": body.ip,
            "username": body.username,
            "password": body.password
        }
        client_info = jsonobject.loads(simplejson.dumps(client_info))
        pidfile = os.path.join(self.serial_pid_dir, "host-%s.pid" % body.ip.replace('.', '_'))
        self._stop_shellinabox_console(client_info, pidfile)
        return jsonobject.dumps(rsp)