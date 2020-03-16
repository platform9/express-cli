"""
Classes to interact with express-cli datamodel
"""

import os
import json
from pf9.exceptions import CLIException
from pf9.modules.util import Logger, Lock

logger = Logger(os.path.join(os.path.expanduser("~"), 'pf9/log/pf9ctl.log')).get_logger(__name__)


class DataModel:
    """Express CLI datamodel"""
    def __init__(self, model_file, model_data=""):
        if model_file:
            self.model_file = model_file
        else:
            except_msg = "DataModel requires "
            raise CLIException
        self.model_data = model_data

    def validate_region_config(self, region_config):

        region_config = {
            'url': "",
            'username': "",
            'password': "",
            'region': "",
            'tenant': "",
            'region_proxy': "-",
            'du_type': ""
        }
        return region_config

    def write(self):
        """Write a datamodel to disk"""

        # initialize locking - NOTE: make sure to release_local() prior to all exceptions/returns)
        lock = Lock() # TODO: Lock() needs to take a file (with path) to know where to create/name lockfile
        # get lock (for concurrent datamodel access across)
        lock.get_lock()

        current_host_profile = get_host_profiles()
        if len(current_host_profile) == 0:
            current_host_profile.append(host_profile)
            with open(globals.HOST_PROFILE_FILE, 'w') as outfile:
                json.dump(current_host_profile, outfile)
        else:
            update_profile = []
            flag_found = False
            for profile in current_host_profile:
                if profile['host_profile_name'] == host_profile['host_profile_name']:
                    update_profile.append(host_profile)
                    flag_found = True
                else:
                    update_profile.append(profile)
            if not flag_found:
                update_profile.append(host_profile)
            with open(globals.HOST_PROFILE_FILE, 'w') as outfile:
                json.dump(update_profile, outfile)

        # release lock
        lock.release_lock()


