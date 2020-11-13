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
    with c.new_session(dest_mac="b4:96:91:32:23:a8", vlan=1708) as session:
        resp = session.send_file("/tmp/passwd.sh")
        logger.info("return: %s" % resp)
    with c.new_session(dest_mac="b4:96:91:32:23:a8", vlan=1708) as session:
        resp = session.exec_cmd("bash /tmp/passwd.sh")
        logger.info("return: %s" % resp)


if __name__ == '__main__':
    main()
    exit(0)
