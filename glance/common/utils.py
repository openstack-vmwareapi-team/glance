# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
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

"""
System-level utilities and helper functions.
"""

import datetime
import errno
import inspect
import logging
import os
import random
import subprocess
import socket
import sys

from glance.common import exception

TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def bool_from_string(subject):
    """
    Interpret a string as a boolean.

    Any string value in:
        ('True', 'true', 'On', 'on', '1')
    is interpreted as a boolean True.

    Useful for JSON-decoded stuff and config file parsing
    """
    if isinstance(subject, bool):
        return subject
    elif isinstance(subject, int):
        return subject == 1
    if hasattr(subject, 'startswith'):  # str or unicode...
        if subject.strip().lower() in ('true', 'on', '1'):
            return True
    return False


def import_class(import_str):
    """Returns a class from a string including module and class"""
    mod_str, _sep, class_str = import_str.rpartition('.')
    try:
        __import__(mod_str)
        return getattr(sys.modules[mod_str], class_str)
    except (ImportError, ValueError, AttributeError), e:
        raise exception.ImportFailure(import_str=import_str,
                                      reason=e)


def import_object(import_str):
    """Returns an object including a module or module and class"""
    try:
        __import__(import_str)
        return sys.modules[import_str]
    except ImportError:
        cls = import_class(import_str)
        return cls()


def abspath(s):
    return os.path.join(os.path.dirname(__file__), s)


def debug(arg):
    logging.debug('debug in callback: %s', arg)
    return arg


def generate_uid(topic, size=8):
    return '%s-%s' % (topic, ''.join(
        [random.choice('01234567890abcdefghijklmnopqrstuvwxyz')
         for x in xrange(size)]))


def generate_mac():
    mac = [0x02, 0x16, 0x3e, random.randint(0x00, 0x7f),
           random.randint(0x00, 0xff), random.randint(0x00, 0xff)]
    return ':'.join(map(lambda x: "%02x" % x, mac))


def last_octet(address):
    return int(address.split(".")[-1])


def isotime(at=None):
    if not at:
        at = datetime.datetime.utcnow()
    return at.strftime(TIME_FORMAT)


def parse_isotime(timestr):
    return datetime.datetime.strptime(timestr, TIME_FORMAT)


def safe_mkdirs(path):
    try:
        os.makedirs(path)
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise


def safe_remove(path):
    try:
        os.remove(path)
    except OSError, e:
        if e.errno != errno.ENOENT:
            raise


class LazyPluggable(object):
    """A pluggable backend loaded lazily based on some value."""

    def __init__(self, pivot, **backends):
        self.__backends = backends
        self.__pivot = pivot
        self.__backend = None

    def __get_backend(self):
        if not self.__backend:
            backend_name = self.__pivot.value
            if backend_name not in self.__backends:
                raise exception.Error('Invalid backend: %s' % backend_name)

            backend = self.__backends[backend_name]
            if type(backend) == type(tuple()):
                name = backend[0]
                fromlist = backend[1]
            else:
                name = backend
                fromlist = backend

            self.__backend = __import__(name, None, None, fromlist)
            logging.info('backend %s', self.__backend)
        return self.__backend

    def __getattr__(self, key):
        backend = self.__get_backend()
        return getattr(backend, key)
