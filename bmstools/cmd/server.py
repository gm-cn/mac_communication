# coding=utf-8
import logging
import sys
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

sys.path.insert(0, BASE_DIR)
from bmstools.utils import log
from bmstools.pkg.server import server


logger = logging.getLogger(__name__)


def main():
    log.setup()

    s = server.get_server()
    s.run()


if __name__ == '__main__':
    main()
