import sys
import logging
import traceback
from oslo_config import cfg
from baremetal import opts
from baremetal.base_agent import BaremetalDaemon
from baremetal.common import utils, log

logger = logging.getLogger(__name__)
CONF = cfg.CONF


def main():
    opts.register_all_options()
    opts.prepare()

    log.setup()
    utils.prepare_pid_dir(CONF.pidfile)
    try:
        agentdaemon = BaremetalDaemon(CONF.pidfile)
        logger.debug('baremetal api service starts')
        agentdaemon.start()
        sys.exit(0)
    except Exception:
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()
