import os
import time
import requests
import socket
import logging
from pf9.exceptions import CLIException, FileLockException
from logging.handlers import TimedRotatingFileHandler


class Utils:
    """Resolve IP of an FQDN and return IP as a string"""
    @staticmethod
    def ip_from_dns_name(fqdn):
        return str(socket.gethostbyname_ex(fqdn)[2][0])


class Logger:
    def __init__(self, log_file):
        self.FORMATTER = logging.Formatter("%(asctime)s — %(name)s — %(levelname)s — %(message)s")
        self.LOG_FILE = log_file

    def get_file_handler(self):
        file_handler = TimedRotatingFileHandler(self.LOG_FILE, when='midnight')
        file_handler.setFormatter(self.FORMATTER)
        return file_handler

    def get_logger(self, logger_name):
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(self.get_file_handler())
        logger.propagate = False
        return logger


class Lock:
    """File locking to protect concurrent write access"""
    TIMEOUT = 10

    def __init__(self, file_to_lock):
        self.file_to_lock = file_to_lock
        # NOT TESTED!!!!!
        self.lock_file = os.path.join(self.file_to_lock + '.lock')

    def lock_assert(self, except_msg=None):
        self.release_lock()
        raise FileLockException(except_msg)

    def get_lock(self):
        cur_time = time.time()
        timeout_start = cur_time
        end_time = timeout_start + self.TIMEOUT
        while cur_time < end_time:
            try:
                os.mkdir(self.lock_file)
                break
            except Exception:
                time.sleep(1)
            cur_time = time.time()

        # enforce timeout
        if cur_time >= end_time:
            self.lock_assert("ERROR: failed to get lock: {} - TIMEOUT EXCEEDED".format(self.lock_file))
        if not os.path.isdir(self.lock_file):
            self.lock_assert("ERROR: failed to get lock: {}".format(self.lock_file))

    def release_lock(self):
        if os.path.isdir(self.lock_file):
            try:
                os.rmdir(self.lock_file)
            except Exception as except_msg:
                self.lock_assert("ERROR: failed to release lock: {}".format(self.lock_file))
        if os.path.isfile(self.lock_file):
            self.lock_assert("ERROR: failed to release lock: {}".format(self.lock_file))


class Pf9ExpVersion:
    """ Methods for managing PF9 Versions"""
    def get_local(self, path):
        try:
            with open(path, 'r') as value:
                version = value.readline().strip()
            return version
        except Exception:
            msg = "Failed reading {}: ".format(path)
            raise CLIException(msg)

    def get_release_json(self, release='latest'):
        req = requests.get('https://api.github.com/repos/platform9/express/releases/' + release)
        response = req.json()
        json_return = {
            "version": response["name"],
            "url_tar": response["tarball_url"],
            "url_zip": response["zipball_url"]
            }
        return json_return

    def get_release(self, release='latest'):
        req = requests.get('https://api.github.com/repos/platform9/express/releases/' + release)
        response = req.json()
        return response["name"]

    def get_release_list(self):
        rel_list = []
        req = requests.get('https://api.github.com/repos/platform9/express/releases')
        response = req.json()
        for rel in response:
            rel_list.append(rel['tag_name'])
        return rel_list
