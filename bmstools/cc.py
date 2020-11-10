import threading
import logging
from time import sleep

from pkg.client import client

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    aa = client.get_client()
    aa.start()
    session = aa.new_session(dest_mac="b4:96:91:33:68:d0", vlan="1731")
    session.init_conn()
    session.send_file("/tmp/aaa")
    session.close_conn()
    resp = session.exec_cmd("ls /root")