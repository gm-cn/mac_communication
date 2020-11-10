import threading
import logging
from time import sleep

from pkg.server import server

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    aa = server.get_server()
    aa.run()