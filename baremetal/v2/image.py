import logging
from oslo_config import cfg
from baremetal.common import jsonobject, utils, http, exceptions
from baremetal.v2 import models
from baremetal.common.exceptions import BmsCodeMsg
from baremetal.constants import V2_REQUEST_ID


logger = logging.getLogger(__name__)
CONF = cfg.CONF


class ImagePlugin_v2(object):
    def __init__(self):
        self.image_path = CONF.pxe.user_image_dir

    @utils.replyerror_v2
    def checkout_image(self, req):
        body = jsonobject.loads(req[http.REQUEST_BODY])
        header = req[http.REQUEST_HEADER]
        logger.debug("image check taskuuid:%s body:%s" % (header[V2_REQUEST_ID], req[http.REQUEST_BODY]))

        rsp = models.AgentResponse()
        rsp.requestId = header[V2_REQUEST_ID]
        res = utils.check_image_exist(self.image_path, body.os_version)
        if not res:
            raise exceptions.ImageCheckV2Error(BmsCodeMsg.IMAGE_ERROR, os_version=body.os_version,
                                                     error="The image template is not exist")
        return jsonobject.dumps(rsp)
