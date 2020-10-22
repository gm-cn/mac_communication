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
    def __init__(self, success=True, error=None):
        self.success = success
        self.error = error if error else ''


class SetSwitchResponse(AgentResponse):
    def __init__(self):
        super(SetSwitchResponse, self).__init__()


class InitImageResponse(AgentResponse):
    def __init__(self):
        super(InitImageResponse, self).__init__()


class IPMIResponse(AgentResponse):
    def __init__(self):
        super(IPMIResponse, self).__init__()
        self.status = []


class GetLan1MACResponse(AgentResponse):
    def __init__(self):
        super(GetLan1MACResponse, self).__init__()
        self.macs = []


class GetVolumePathResponse(AgentResponse):
    def __init__(self):
        super(GetVolumePathResponse, self).__init__()
        self.volume_path = None


class GetSwitchRelationsResp(AgentResponse):
    def __init__(self):
        super(GetSwitchRelationsResp, self).__init__()
        self.relations = []

class SerialConsoleOpenResponse(AgentResponse):
    def __init__(self):
        super(SerialConsoleOpenResponse, self).__init__()
        self.url = None

class ConvertCustomImage(AgentResponse):
    def __init__(self):
        super(ConvertCustomImage, self).__init__()
        self.custom_image_name = None

class GetHostRealNicMacListResponse(AgentResponse):
    def __init__(self):
        super(GetHostRealNicMacListResponse, self).__init__()
        self.data = None