# Copyright 2017 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import itertools

import logging
import tenacity
from tooz import coordination

logger = logging.getLogger(__name__)


class PoolLock(object):
    """Tooz lock wrapper for pools of locks

    If tooz coordinator is provided, it will attempt to grab any lock
    from a predefined set of names, with configurable set size (lock pool),
    and keep attempting for until given timeout is reached.

    """

    def __init__(self, coordinator, locks_pool_size=1, locks_prefix='sw-',
                 timeout=0):
        self.coordinator = coordinator
        self.locks_prefix = locks_prefix
        self.lock_names = ("{}-{}".format(locks_prefix, i)
                           for i in range(locks_pool_size))
        self.locks_pool_size = locks_pool_size
        self.timeout = timeout

    def __enter__(self):
        self.lock = False
        if not self.coordinator:
            return self

        logger.debug("Trying to acquire lock for %s", self.locks_prefix)
        names = itertools.cycle(self.lock_names)
        retry_kwargs = {'wait': tenacity.wait_random(min=0, max=1),
                        'reraise': True}
        if self.timeout:
            retry_kwargs['stop'] = tenacity.stop_after_delay(self.timeout)

        @tenacity.retry(**retry_kwargs)
        def grab_lock_from_pool():
            name = next(names)
            # NOTE(pas-ha) currently all tooz backends support locking API.
            # In case this changes, this should be wrapped to not respin
            # lock grabbing on NotImplemented exception.
            lock_name = name.encode()
            lock = self.coordinator.get_lock(lock_name)
            locked = lock.acquire(blocking=False)
            if not locked:
                raise coordination.LockAcquireFailed(
                    "Failed to acquire lock %s" % name)
            logger.debug("lock[%s] is acquired." % lock_name)
            return lock, lock_name

        try:
            self.lock, self.lock_name = grab_lock_from_pool()
        except Exception:
            msg = ("Failed to acquire any of %s locks for %s "
                   "for a netmiko action in %s seconds. "
                   "Try increasing acquire_timeout." % (
                       self.locks_pool_size, self.locks_prefix,
                       self.timeout))
            logger.error(msg, exc_info=True)
            raise
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.lock:
            self.lock.release()
            logger.debug("release lock %s", self.lock_name)
