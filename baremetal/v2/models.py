class ModelBase(object):

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            self[k] = v

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __getitem__(self, key):
        return getattr(self, key)

    def __eq__(self, other):
        if not hasattr(other, 'uuid'):
            return False
        return type(other) == type(self) and other.uuid == self.uuid

    def __ne__(self, other):
        return not self == other

    def is_valid(self):
        self.errors = {}
        self._validate(self.errors)
        return self.errors == {}

    def to_dict(self):
        return self.__dict__.copy()

    def _validate(self, errors):
        pass


class AgentResponse(object):
    def __init__(self, code="Success", msg=None, requestId=None):
        self.code = code
        self.msg = msg if msg else ''
        self.requestId = requestId


class IPMIResponse(AgentResponse):
    def __init__(self):
        super(IPMIResponse, self).__init__()


class IPMIStatusResponse(AgentResponse):
    def __init__(self):
        super(IPMIStatusResponse, self).__init__()
        self.data = {}


class SetSwitchResponse(AgentResponse):
    def __init__(self):
        super(SetSwitchResponse, self).__init__()


class GetSwitchRelationsResp(AgentResponse):
    def __init__(self):
        super(GetSwitchRelationsResp, self).__init__()
        self.data = []


class BiosconfigSet(AgentResponse):
    def __init__(self):
        super(BiosconfigSet, self).__init__()


class BiosInfo(AgentResponse):
    def __init__(self):
        super(BiosInfo, self).__init__()
        self.data = {}


class HardwareTest(AgentResponse):
    def __init__(self):
        super(HardwareTest, self).__init__()
        self.data = {}

class GetSwitchSn(AgentResponse):
    def __init__(self):
        super(GetSwitchSn, self).__init__()
        self.data = {}
