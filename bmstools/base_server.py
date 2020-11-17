import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

sys.path.insert(0, BASE_DIR)

from bmstools.utils import auth
from bmstools.pkg.server import server
from bmstools.utils import daemon

_rest_service = None

def new_rest_service():
    global _rest_service
    if not _rest_service:
        _rest_service = InitService()
    return _rest_service


class InitService(object):
    def __init__(self):
        self.private_key, self.public_key = auth.gen_key()

    def start(self):
        with open(os.path.join("/usr/lib/python2.7/site-packages/bmstools/pkg/server/private.pem"), "w") as f:
            f.write(self.private_key)
        with open(os.path.join("/usr/lib/python2.7/site-packages/bmstools/pkg/server/public.pem"), "w") as f:
            f.write(self.public_key)
        s = server.get_server()
        s.run()


class BaremetalDaemon(daemon.Daemon):
    def run(self):
        self.agent = new_rest_service()
        self.agent.start()
