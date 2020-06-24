import contextlib
import functools
import json
import logging
import os
import shutil
import hashlib
import tempfile
import traceback

import time

import jinja2
from oslo_concurrency import processutils
from oslo_config import cfg

from baremetal.common import jsonobject, exceptions
from baremetal.conductor import models as models_v1
from baremetal.v2 import models as models_v2
from baremetal.constants import V2_REQUEST_ID
import subprocess

logger = logging.getLogger(__name__)

temp_dir="/tmp"
CONF = cfg.CONF


@contextlib.contextmanager
def tempdir(**kwargs):
    argdict = kwargs.copy()
    if 'dir' not in argdict:
        argdict['dir'] = temp_dir
    tmpdir = tempfile.mkdtemp(**argdict)
    try:
        yield tmpdir
    finally:
        try:
            shutil.rmtree(tmpdir)
        except OSError as e:
            logger.error('Could not remove tmpdir: %s', e)


def retry(times=3, sleep_time=3):
    def decorator(f):
        @functools.wraps(f)
        def inner(*args, **kwargs):
            for _ in range(0, times):
                try:
                    return f(*args, **kwargs)
                except:
                    time.sleep(sleep_time)
            raise
        return inner
    return decorator


def mkfs(fs, path, label=None):
    args = ['mkfs', '-t', fs]
    if label:
        args.extend(['-n', label])
    args.append(path)
    processutils.execute(*args)


def mount(device, mountpoint, fstype=None, options=None):
    mount_cmd = ['mount']
    if fstype:
        mount_cmd.extend(['-t', fstype])
    if options is not None:
        mount_cmd.extend(options)
    mount_cmd.extend([device, mountpoint])
    processutils.execute(*mount_cmd)


def umount(mountpoint):
    processutils.execute('umount', mountpoint)


def execute(*cmd, **kwargs):
    result = processutils.execute(*cmd, **kwargs)
    return result


def dd(src, dst, *args):
    execute('dd', 'if=%s' % src, 'of=%s' % dst, *args)


def remove_tree(path):
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        if os.path.isfile(path):
            os.remove(path)
    except OSError as e:
        logger.warning("Failed to remove dir %(path)s, error: %(e)s",
                    {'path': path, 'e': e})
        raise e


def mkdir(path):
    try:
        if not os.path.exists(path):
            os.makedirs(path, 0o755)
        else:
            pass
    except OSError as e:
        logger.warning("Failed to mkdir %(path)s, error: %(e)s",
                    {'path': path, 'e': e})
        raise e


def get_context_from_template(filename):
    template = './template/%s.json' % filename

    with open(template) as f:
        body = json.load(f)

    return body


def prepare_pid_dir(path):
    pdir = os.path.dirname(path)
    if not os.path.isdir(pdir):
        os.makedirs(pdir)


def replyerror(func):
    @functools.wraps(func)
    def wrap(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            logger.debug(traceback.format_exc())
            rsp = models_v1.AgentResponse()
            rsp.success = False
            rsp.error = exc._error_string if hasattr(exc, '_error_string') \
                else str(exc)
            return jsonobject.dumps(rsp)
    return wrap


def replyerror_v2(func):
    @functools.wraps(func)
    def wrap(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            logger.debug(traceback.format_exc())
            rsp = models_v2.AgentResponse()
            rsp.code = exc.code if hasattr(exc, 'code') else False
            rsp.requestId = args[1]["header"][V2_REQUEST_ID]
            rsp.msg = exc._error_string if hasattr(exc, '_error_string') \
                else str(exc)
            return jsonobject.dumps(rsp)
    return wrap


def wait_callback_success(callback, callback_data=None,
                          timeout=60,
                          interval=1,
                          ignore_exception_in_callback=False):
    '''
    Wait for callback(callback_data) return none 'False' result, until the
    timeout. After each 'False' return, will sleep for an interval, before
    next calling. When callback result is not 'False', will directly return
    the result. When timeout, it will return False.

    If callback meets exception, it will defaultly directly return False,
    unless exception_result is set to True.
    '''
    count = time.time()
    timeout = timeout + count
    while count <= timeout:
        try:
            rsp = callback(callback_data)
            if rsp:
                return rsp
            time.sleep(interval)
            count = time.time()
        except Exception as e:
            if not ignore_exception_in_callback:
                logger.debug(traceback.format_exc())
                raise e
            time.sleep(interval)

    return False


def get_volume_path(dev_id):
    base_dir = "/dev/disk/by-id/"
    wwn_id = CONF.hitachi.wwn_id
    volume_path = None
    for dev in os.listdir(base_dir):
        if dev.startswith(wwn_id) and dev.endswith(str(dev_id)):
            if volume_path:
                error_msg = "query at least two volume path."
                raise exceptions.GetVolumePathError(error=error_msg)
            volume_path = os.path.join(base_dir, dev)
    return volume_path


def render_template(template, params, is_file=True):
    if is_file:
        tmpl_path, tmpl_name = os.path.split(template)
        loader = jinja2.FileSystemLoader(tmpl_path)
    else:
        tmpl_name = 'template'
        loader = jinja2.DictLoader({tmpl_name: template})
    env = jinja2.Environment(loader=loader)
    tmpl = env.get_template(tmpl_name)
    return tmpl.render(params, enumerate=enumerate)


def list_dict_duplicate_removal(data):
    run_function = lambda x, y: x if y in x else x + [y]
    return reduce(run_function, [[], ] + data)


def validate_image(image_path):
    checksum_path = image_path + '_checksum'
    if os.path.exists(checksum_path):
        logger.debug("%s is exist" % checksum_path)
        return True
    else:
        # hash_value = hashlib.md5()
        # with open(image_path, "rb") as f:
        #     maxbuf = 1024 * 1024  # bytes
        #     while True:
        #         buf = f.read(maxbuf)
        #         if not buf:
        #             break
        #         hash_value.update(buf)
        # checksum = hash_value.hexdigest()
        # with open(checksum_path, "w") as f:
        #     f.write(checksum)
        logger.debug("%s is not exist" % checksum_path)
        return False


def check_image_exist(image_path, image_name):
    all_images = os.walk(image_path)
    root_path, sub_path, files = all_images.next()
    if image_name in files:
        image_path = os.path.join(image_path, image_name)
        return validate_image(image_path)
    else:
        return False


def query_task(task_id, pid):
    log_file = "/tmp/{0}.log".format(task_id)
    extra = {
        "progress": "-",
        "speed": "-",
        "transfered": "-",
        "elapsed": "-",
        "total": "-",
    }
    if not os.path.exists(log_file):
        return extra

    args = ["tail", "-c", "512", log_file]
    p = subprocess.Popen(args, stdout=subprocess.PIPE)

    content = p.stdout.read().decode("utf-8")
    lines = content.split("\n")
    i = 0
    arr = []
    for line in lines:
        if not line:
            continue
        ss = line.split('\r')
        if len(ss) > 1:
            arr.append(ss[-1])
        else:
            arr.append(line)
    extra = parse_transfer_result(arr)
    patch_task_status(extra, pid)
    return extra

def parse_transfer_result(lines):
    """
    [receiving incremental file list,
        100M.iso,
        19,759,104  18%    1.88MB/s    0:00:44
    ]

    [24,936,448  23%    2.08MB/s    0:00:37]

    [   104,857,600 100%    1.92MB/s    0:00:52 (xfr#1, to-chk=0/1),
        sent 43 bytes  received 104,883,295 bytes  1,446,666.73 bytes/sec,
        total size is 104,857,600  speedup is 1.00
    ]
    """

    transfered = "transfered"
    total = "total"
    speed = "speed"
    progress = "progress"
    elapsed = "elapsed"
    extra = {
        progress: "-",
        speed: "-",
        transfered: "-",
        elapsed: "-",
        total: "-",
    }
    for line in lines:
        if line.count("receiving") > 0:
            continue
        arr = line.split()
        if len(arr) == 1:
            continue
        if arr[0] == "sent":
            extra[speed] = arr[6]
            extra[progress] = "100%"
        elif arr[0] == "total":
            extra[total] = arr[3]
        elif len(arr) == 4:
            extra[transfered] = arr[0]
            extra[progress] = arr[1]
            extra[speed] = arr[2]
            extra["elapsed"] = arr[3]
        elif arr[1] == "100%":
            extra[transfered] = arr[0]
            extra[progress] = arr[1]
            extra["elapsed"] = arr[3]
    if progress in extra:
        extra[progress] = extra[progress].replace('%', '')
    return extra


def patch_task_status(extra, pid):
    """Patch task status."""
    if extra.get("progress") == '100':
        extra["status"] = 'done'
        return
    args = "ps {0}".format(pid)
    try:
        output = subprocess.check_output(args, shell=True)
    except subprocess.CalledProcessError:
        extra["status"] = "failed"
        return

    lines = output.split("\n")
    if len(lines) < 2:
        extra["status"] = "failed"
        return
    row = lines[1].split()
    if len(row) < 5:
        extra["status"] = '-'
    extra["status"] = "doing"

