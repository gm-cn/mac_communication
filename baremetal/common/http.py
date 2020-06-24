import copy
import traceback
import types
import simplejson
import logging
import uuid
import thread
import urllib3
import cherrypy

from baremetal.common import jsonobject
from baremetal.common import utils

TASK_UUID = 'taskuuid'
ERROR_CODE = 'error'
REQUEST_HEADER = 'header'
REQUEST_BODY = 'body'
QUERY_STRING = "params"
CALLBACK_URI = 'callbackuri'

logger = logging.getLogger(__name__)


class SyncUri(object):
    def __init__(self):
        self.uri = None
        self.func = None
        self.controller = None


class AsyncUri(SyncUri):
    def __init__(self):
        super(AsyncUri, self).__init__()
        self.callback_uri = None


class Request(object):
    def __init__(self):
        self.headers = None
        self.body = None
        self.method = None
        self.query_string = None

    @staticmethod
    def from_cherrypy_request(creq):
        req = Request()
        req.headers = copy.copy(creq.headers)
        req.body = creq.body.fp.read() if creq.body else None
        req.method = copy.copy(creq.method)
        req.query_string = copy.copy(creq.query_string) if creq.query_string else None
        return req


class SyncUriHandler(object):
    def _check_response(self, rsp):
        if rsp is not None and not isinstance(rsp, types.StringType):
            raise Exception('Response body must be string')

    def __init__(self, uri_obj):
        self.uri_obj = uri_obj

    def _do_index(self, req):
        cherrypy.request.headers.pop("callbackuri", None)
        cherrypy.request.headers.pop("taskuuid", None)

        entity = {REQUEST_HEADER: req.headers}
        params = {}
        if req.query_string:
            params = self.query_string_to_object(req.query_string)
        entity[REQUEST_BODY] = req.body if req.body else params
        return self.uri_obj.func(entity)

    @cherrypy.expose
    def index(self, **kwargs):
        req = Request.from_cherrypy_request(cherrypy.request)
        try:
            task_uuid = req.headers["Taskuuid"]
        except:
            req.headers["Taskuuid"] = str(uuid.uuid4())
        logger.debug('sync http call: %s' %
                     req.body if req.body else req.query_string)
        rsp = self._do_index(req)
        self._check_response(rsp)
        return rsp

    @staticmethod
    def query_string_to_object(query_string):
        params = {}
        pairs = query_string.split('&')
        for p in pairs:
            (k, v) = p.split('=')
            params[k] = v
        return params


class AsyncUriHandler(SyncUriHandler):
    def __init__(self, uri_obj):
        super(AsyncUriHandler, self).__init__(uri_obj)

    @thread.AsyncThread
    def _run_index(self, task_uuid, callback_uri, request, filename=None, step=None):
        headers = {TASK_UUID: task_uuid, "step": step}

        try:
            content = super(AsyncUriHandler, self)._do_index(request)
            self._check_response(content)
            # only use test
            if filename:
                with open(filename, 'w') as f:
                    data = simplejson.dumps(content)
                    f.write(data)
                    f.flush()
        except Exception:
            logger.error(traceback.format_exc())
            headers[ERROR_CODE] = content
        json_post(callback_uri, content, headers)

    @cherrypy.expose
    def index(self):

        task_uuid = cherrypy.request.headers.get(TASK_UUID, None)
        step = cherrypy.request.headers.get("step", None)
        filename = cherrypy.request.headers.get('filename', None)
        logger.debug('******* filename:%s' % filename)

        req = Request.from_cherrypy_request(cherrypy.request)
        if not task_uuid:
            task_uuid = str(uuid.uuid4())
            req.headers["Taskuuid"] = task_uuid
            #err = 'taskuuid missing in request header'
            #logger.warn(err)
            #raise cherrypy.HTTPError(400, err)

        callback_uri = cherrypy.request.headers.get(CALLBACK_URI)
        logger.debug('async http call[task uuid: %s], body: %s' % (task_uuid, req.body))
        print 'async http call[task uuid: %s], body: %s' % (task_uuid, req.body)
        self._run_index(task_uuid, callback_uri, req, filename, step)


class HttpServer(object):

    def __init__(self, host='0.0.0.0', port=8080, async_callback_uri=None):
        '''
        Constructor
        '''
        self.async_callback_uri = async_callback_uri
        self.async_uri_handlers = {}
        self.sync_uri_handlers = {}
        self.server = None
        self.server_conf = None
        self.host = host
        self.port = port
        self.mapper = None

    def register_async_uri(self, uri, func, callback_uri=None):
        async_uri_obj = AsyncUri()
        async_uri_obj.callback_uri = callback_uri
        if async_uri_obj.callback_uri is None:
            async_uri_obj.callback_uri = self.async_callback_uri
        async_uri_obj.uri = uri
        async_uri_obj.func = func
        async_uri_obj.controller = AsyncUriHandler(async_uri_obj)

        self.async_uri_handlers[uri] = async_uri_obj

    def register_sync_uri(self, uri, func):
        sync_uri = SyncUri()
        sync_uri.func = func
        sync_uri.uri = uri
        sync_uri.controller = SyncUriHandler(sync_uri)
        self.sync_uri_handlers[uri] = sync_uri

    def unregister_uri(self, uri):
        del self.async_callback_uri[uri]

    def _add_mapping(self, uri_obj):
        if not self.mapper:
            self.mapper = cherrypy.dispatch.RoutesDispatcher()
        self.mapper.connect(name=uri_obj.uri, route=uri_obj.uri,
                            controller=uri_obj.controller, action="index")
        logger.debug('function[%s] registered uri: %s' % (uri_obj.func.__name__, uri_obj.uri))

    def _build(self):
        for akey in self.async_uri_handlers.keys():
            aval = self.async_uri_handlers[akey]
            self._add_mapping(aval)
        for skey in self.sync_uri_handlers.keys():
            sval = self.sync_uri_handlers[skey]
            self._add_mapping(sval)

        self.server_conf = {'request.dispatch': self.mapper}

        cherrypy.engine.autoreload.unsubscribe()
        # cherrypy.engine.thread_manager.unsubscribe()
        site_config = {}
        site_config['server.socket_host'] = self.host
        site_config['server.socket_port'] = self.port
        cherrypy.config.update(site_config)

        self.server = cherrypy.tree.mount(root=None,
                                          config={'/': self.server_conf})
        cherrypy.log.error_file = ""
        cherrypy.log.access_file = ""
        cherrypy.log.screen = False
        self.server.log.error_file = ''
        self.server.log.access_file = ''
        self.server.log.screen = False
        self.server.log.access_log = logger
        self.server.log.error_log = logger

    def start(self):
        self._build()
        logger.info('host: %s port: %s' % (self.host, self.port))
        cherrypy.quickstart(self.server)

    @thread.AsyncThread
    def start_in_thread(self):
        self.start()

    @staticmethod
    def query_string_to_object(query_string):
        params = {}
        pairs = query_string.split('&')
        for p in pairs:
            (k, v) = p.split('=')
            params[k] = v
        return params

    def stop(self):
        cherrypy.engine.exit()


def json_post(uri, body=None, headers={}, method='POST', fail_soon=False):
    ret = []

    def post(_):
        try:
            pool = urllib3.PoolManager(timeout=120.0, retries=urllib3.util.retry.Retry(15))
            header = {'Content-Type': 'application/json', 'Connection': 'close'}
            for k in headers.keys():
                header[k] = headers[k]

            if body is not None:
                assert isinstance(body, types.StringType)
                header['Content-Length'] = str(len(body))
                content = pool.urlopen(method, uri, headers=header, body=str(body)).data
                logger.debug("json_post url: %s, header:%s data: %s" % (uri, str(header), str(body)))
            else:
                header['Content-Length'] = '0'
                content = pool.urlopen(method, uri, headers=header).data

            pool.clear()
            ret.append(content)
            return True
        except Exception as e:
            logger.error(traceback.format_exc())
            if fail_soon:
                raise e
            return False

    if fail_soon:
        post(None)
    else:
        if not utils.wait_callback_success(post, ignore_exception_in_callback=True):
            raise Exception('unable to post to %s, body: %s, see before error' % (uri, body))

    return ret[0]


def json_dump_post(uri, body=None, headers={}, fail_soon=False):
    content = None
    if body is not None:
        content = jsonobject.dumps(body)
    return json_post(uri, content, headers, fail_soon=fail_soon)


def json_dump_get(uri, body=None, headers={}, fail_soon=False):
    content = None
    if body is not None:
        content = jsonobject.dumps(body)
    return json_post(uri, content, headers, 'GET', fail_soon=fail_soon)


class UriBuilder(object):
    def _invalid_uri(self, uri):
        raise Exception('invalid uri[%s]' % uri)

    def _parse(self, uri):
        scheme = uri[0:4]
        if scheme not in ['http', 'https']:
            raise Exception('uri[%s] is not started with scheme[http, https]' % uri)
        self.scheme = scheme

        rest = uri.lstrip(scheme)
        if not rest.startswith('://'):
            self._invalid_uri(uri)

        rest = rest.lstrip('://')
        colon = rest.find(':')
        if colon != -1:
            self.host = rest[0:colon]
            rest = rest.lstrip(self.host).lstrip(':%s' % self.port)
        else:
            self.port = 80
            slash = rest.find('/')
            if slash == -1:
                self.host = rest[0:]
                return
            else:
                self.host = rest[0:slash]

        self.paths = [p.strip('/') for p in rest.split('/')]
        if '' in self.paths:
            self.paths.remove('')
        self.paths = [] if not self.paths else self.paths

    def __init__(self, uri=None):
        self.scheme = 'http'
        self.host = None
        self.port = 7073
        self.paths = []
        if uri:
            self._parse(uri)

    def add_path(self, p):
        self.paths.append(p)

    def build(self):
        if not self.host:
            raise Exception('host cannot be None')

        self.paths = [p.strip('/') for p in self.paths]
        path = '/'.join(self.paths)
        ret = '%s://%s:%s/%s' % (self.scheme, self.host, self.port, path)
        return ret + '/' if not ret.endswith('/') else ret


def build_url(args):
    builder = UriBuilder()
    builder.scheme = args[0]
    builder.host = args[1]
    builder.port = args[2]
    builder.paths = args[3:]
    return builder.build()


def path_msg(path, msg=None):
    return path if not msg else '%s %s' % (path, msg)
