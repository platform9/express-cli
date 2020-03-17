import requests
from ..exceptions import CLIException
import socket
import logging
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
