# coding=utf-8
import logging
import sys
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

sys.path.insert(0, BASE_DIR)
from bmstools.utils import log
from bmstools.pkg.client import client


logger = logging.getLogger(__name__)


def main():
    log.setup()

    c = client.get_client()
    c.start()
    with c.new_session(dest_mac="\xb4\x96\x91\x32\x23\xa8", src_mac="\xb4\x96\x91\x33\x68\xd0", vlan=1708) as session:
        resp = session.exec_cmd("ls /root")
        logger.info("return: %s" % resp)
    with c.new_session(dest_mac="\xb4\x96\x91\x2f\xcb\x40", src_mac="\xb4\x96\x91\x32\x31\xd8", vlan=1800) as session:
        resp = session.exec_cmd("cat /root/get")
        logger.info("return: %s" % resp)


if __name__ == '__main__':
    main()
    exit(0)
