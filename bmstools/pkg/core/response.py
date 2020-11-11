# coding=utf-8
import json
import logging


logger = logging.getLogger(__name__)


class Code(object):
    Success = "Success"

    AnalyzeError = "AnalyzeError"
    LogicError = "LogicError"
    ParameterError = "ParameterError"
    UnknownError = "UnknownError"


class Response(object):

    def __init__(self, code='', msg='', data=None):
        self.code = code
        self.msg = msg
        self.data = data

    def pack(self):
        r = {"code": self.code}
        if self.msg:
            r["msg"] = self.msg
        if self.data:
            r["data"] = self.data
        return json.dumps(r)

    @classmethod
    def unpack(cls, data):
        r = json.loads(data)
        return cls(r.get('code'), r.get('msg', ''), r.get('data'))


class TException(Exception):

    def __init__(self, code, msg):
        self.code = code
        self.msg = msg
        super(TException, self).__init__('%s: %s' % (code, msg))
