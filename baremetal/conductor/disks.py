import gzip
import math
import os
import re
import shlex
import shutil
import tempfile

import logging
import traceback

import six
import time
from oslo_serialization import base64
from oslo_utils import units

from baremetal.common import utils, shell, exceptions
from baremetal.conductor import models

logger = logging.getLogger(__name__)

CONFIGDRIVE_LABEL = "config-2"
MAX_CONFIG_DRIVE_SIZE_MB = 64
_PARTED_PRINT_RE = re.compile(r"^(\d+):([\d\.]+)MiB:"
                              "([\d\.]+)MiB:([\d\.]+)MiB:(\w*)::(\w*)")


class DiskConfiguration(models.ModelBase):

    def dd(self, src, dst, conv_flags=None):
        """Execute dd from src to dst."""
        if conv_flags:
            extra_args = ['conv=%s' % conv_flags]
        else:
            extra_args = []

        utils.dd(src, dst, 'bs=1M', 'oflag=direct', *extra_args)

    def get_labelled_partition(self, baremetal_id, device_path):

        shell.call("partprobe %s" % device_path)
        time.sleep(3)
        executor = shell.call("lsblk -Po name,label %s" % device_path)
        output = executor.stdout
        found_part = None
        if output:
            for device in output.split('\n'):
                dev = {key: value for key, value in (v.split('=', 1)
                        for v in shlex.split(device))}
                if not dev:
                    continue
                if dev['LABEL'].upper() == CONFIGDRIVE_LABEL.upper():
                    if found_part:
                        found_2 = '/dev/%(part)s' % {'part': dev['NAME'].strip()}
                        found = [found_part, found_2]
                        logger.debug(('more than one partition with label "config-2" '
                                      'exists on device %s for baremetal[uuid:%s]:%s')
                                     % (device_path, baremetal_id, found))
                    found_part = '/dev/%(part)s' % {'part': dev['NAME'].strip()}

        logger.debug("found_part for baremetal[uuid:%s]: %s" %(baremetal_id, found_part))
        return found_part

    def _get_configdrive(self, configdrive, tempdir=None):

        data = six.BytesIO(base64.decode_as_bytes(configdrive))

        configdrive_file = tempfile.NamedTemporaryFile(delete=False,
                                                       prefix='configdrive',
                                                       dir=tempdir)

        with gzip.GzipFile('configdrive', 'rb', fileobj=data) as gunzipped:
            try:
                shutil.copyfileobj(gunzipped, configdrive_file)
            except Exception as e:
                os.unlink(configdrive_file.name)
                raise e
            else:
                configdrive_file.seek(0, os.SEEK_END)
                bytes_ = configdrive_file.tell()
                configdrive_mb = int(math.ceil(float(bytes_) / units.Mi))
            finally:
                configdrive_file.close()

            return (configdrive_mb, configdrive_file.name)

    def list_partitions(self, device):

        output = utils.execute(
            'parted', '-s', '-m', device, 'unit', 'MiB', 'print')[0]
        if isinstance(output, bytes):
            output = output.decode("utf-8")
        lines = [line for line in output.split('\n') if line.strip()][2:]
        # Example of line: 1:1.00MiB:501MiB:500MiB:ext4::boot
        fields = ('number', 'start', 'end', 'size', 'filesystem', 'flags')
        result = []
        for line in lines:
            match = _PARTED_PRINT_RE.match(line)
            if match is None:
                continue
            # Cast int fields to ints (some are floats and we round them down)
            groups = [int(float(x)) if i < 4 else x
                      for i, x in enumerate(match.groups())]
            result.append(dict(zip(fields, groups)))
        return result

    def count_mbr_partitions(self, device):
        output, err = utils.execute('partprobe', '-d', '-s', device,
                                    run_as_root=True, use_standard_locale=True)
        if 'msdos' not in output:
            raise ValueError('The device %s does not have a valid MBR '
                             'partition table' % device)
        output = output.replace('<', '').replace('>', '')
        partitions = [int(s) for s in output.split() if s.isdigit()]

        return sum(i < 5 for i in partitions), sum(i > 4 for i in partitions)

    def _is_disk_gpt_partitioned(self, device):
        stdout, _stderr = utils.execute(
            'blkid', '-p', '-o', 'value', '-s', 'PTTYPE', device)
        return stdout.lower().strip() == 'gpt'

    def create_config_drive_partition(self, baremetal_id, device, configdrive):
        confdrive_file = None
        try:
            config_drive_part = self.get_labelled_partition(baremetal_id, device)
            confdrive_mb, confdrive_file = self._get_configdrive(configdrive)
            if confdrive_mb > MAX_CONFIG_DRIVE_SIZE_MB:
                logger.error("baremetal[uuid:%s] Config drive size "
                             "exceeds maximum limit of 64MiB." % baremetal_id)
                raise exceptions.BaremetalError(uuid=baremetal_id)

            if config_drive_part:
                logger.debug("Configdrive for node exists at %s" % config_drive_part)
            else:
                cur_parts = set(part['number'] for part in self.list_partitions(device))
                if self._is_disk_gpt_partitioned(device):
                    create_option = '0:-%dMB:0' % MAX_CONFIG_DRIVE_SIZE_MB
                    shell.call("sgdisk -n %s %s" % (create_option, device))
                    shell.call("partprobe %s" % device)
                else:
                    startlimit = '-%dMiB' % MAX_CONFIG_DRIVE_SIZE_MB
                    endlimit = '-0'
                    shell.call("parted -a optimal -s -- %s mkpart primary "
                               "fat32 %s %s" % (device, startlimit, endlimit))

                upd_parts = set(part['number'] for part in self.list_partitions(device))
                new_part = set(upd_parts) - set(cur_parts)
                config_drive_part = '%s%s' % (device, new_part.pop())
                shell.call("udevadm settle")
                shell.call("test -e %s" % config_drive_part)
            self.dd(confdrive_file, config_drive_part)
            logger.debug("Configdrive for node successfully copied "
                         "onto partition %s" % config_drive_part)
        except Exception as ex:
            logger.error(traceback.format_exc())
            raise exceptions.CreatePartitionError(uuid=baremetal_id, error=ex)

        finally:
            if confdrive_file:
                os.unlink(confdrive_file)


