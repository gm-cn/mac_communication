import os
import shutil

import logging
import six

from baremetal.common import utils
from oslo_utils import fileutils
from oslo_utils import units

logger = logging.getLogger(__name__)

CONFIGDRIVESIZE_BYTES = 64 * units.Mi


class ConfigDriveBuilder(object):

    def __init__(self, metadata=None):
        self.imagefile = None
        self.mdfiles = []

        if metadata is not None:
            self.add_metadata(metadata)

    def __enter__(self):
        return self

    def __exit__(self, exctype, excval, exctb):
        if exctype is not None:
            return False

        self.cleanup()

    def add_metadata(self, metadata):
        for (path, data) in metadata.metadata_for_configdrive():
            self.mdfiles.append((path, data))

    def _add_file(self, basedir, path, data):
        filepath = os.path.join(basedir, path)
        dirname = os.path.dirname(filepath)
        fileutils.ensure_tree(dirname)
        with open(filepath, 'wb') as f:
            if isinstance(data, six.text_type):
                data = data.encode('utf-8')
            f.write(data)

    def _make_vfat(self, path, tmpdir):

        with open(path, 'wb') as f:
            f.truncate(CONFIGDRIVESIZE_BYTES)

        utils.mkfs('vfat', path, label='config-2')

        with utils.tempdir() as mountdir:
            mounted = False
            try:
                utils.mount(path, mountdir,
                    options=['-o', 'loop,uid=%d,gid=%d' % (os.getuid(), os.getgid())])

                mounted = True
                for ent in os.listdir(tmpdir):
                    shutil.copytree(os.path.join(tmpdir, ent),
                                    os.path.join(mountdir, ent))
            finally:
                if mounted:
                    utils.umount(mountdir)

    def make_configdrive(self, path):
        with utils.tempdir() as tmpdir:
            self._write_md_files(tmpdir)
            self._make_vfat(path, tmpdir)

    def _write_md_files(self, basedir):
        for data in self.mdfiles:
            self._add_file(basedir, data[0], data[1])

    def cleanup(self):
        if self.imagefile:
            fileutils.delete_if_exists(self.imagefile)

