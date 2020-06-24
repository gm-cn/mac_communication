import logging

from baremetal.common import utils, http, jsonobject
from baremetal.conductor.models import AgentResponse


class DebugResponse(AgentResponse):
    def __init__(self):
        super(DebugResponse, self).__init__()
        self.log = None


logger = logging.getLogger(__name__)


class DebugPlugin(object):

    @utils.replyerror
    def debug(self, req):
        rsp = DebugResponse()
        rsp.log = req[http.REQUEST_BODY]
        logger.debug("###debug result###: %s" % rsp.log)

        return jsonobject.dumps(rsp)

