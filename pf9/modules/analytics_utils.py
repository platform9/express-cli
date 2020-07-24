import analytics
import uuid
import math
import time
import datetime
import os
from pf9.modules.util import Utils, Logger

logger = Logger(os.path.join(os.path.expanduser("~"), 'pf9/log/pf9ctl.log')).get_logger(__name__)

# the write_key is the Segment API authorization and identifier, without this no data submission will work.
analytics.write_key = 'qDQpEaZQnDgqpXXG6jiV7OlZGqYZlQAa'


class SegmentSessionWrapper:
    def __init__(self, ctx):
        self.ctx = ctx

    def load_segment_session(self, segment_session, segment_event_properties, segment_subcommand):
        """Load segment session related objects to ctx
        """
        self.ctx.params["segment_session"] = segment_session
        self.ctx.params["segment_event_properties"] = segment_event_properties
        self.ctx.params["segment_event_prefix"] = 'WZ PMKExpress CLI'
        self.ctx.params["segment_subcommand"] = segment_subcommand
        self.ctx.params["segment_step_count"] = 1

    def reload_segment_session_with_auth(self):
        """
            Reload Segment Session with DU URL and Keystone User ID after keystone Auth
        """
        segment_event_properties = self.ctx.params["segment_event_properties"]
        segment_event_properties.update(du_account_url=self.ctx.params['du_url'])
        segment_event_properties.update(keystone_user_id=self.ctx.params['user_id'])
        self.ctx.params["segment_event_properties"] = segment_event_properties

    def send_track(self, step_name):
        """ Builds event name based on subcommand and step count
        """
        event_name = " - ".join([self.ctx.params["segment_event_prefix"], self.ctx.params["segment_subcommand"],
                              step_name, str(self.ctx.params["segment_step_count"])])
        self.ctx.params["segment_step_count"] = self.ctx.params["segment_step_count"] + 1
        self.ctx.params["segment_session"].send_track(event_name, self.ctx.params["segment_event_properties"], user_id=self.ctx.params['user_id'])

    def send_track_error(self, step_name, error_message):
        error_event_name = " - ".join([self.ctx.params["segment_event_prefix"], self.ctx.params["segment_subcommand"],
                                 "ERROR"])
        segment_properties = self.ctx.params["segment_event_properties"].copy()
        segment_properties.update(dict(error_name=step_name, error_message=str(error_message)))
        # its possible that this was an Authentication Failure, so it might not have user_id
        self.ctx.params["segment_session"].send_track(error_event_name, segment_properties,
                                                      user_id=self.ctx.params.get('user_id', None))


class SegmentSession:

    def __init__(self):
        # unique for the device
        self.device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, str(uuid.getnode())))

        # unique for this session
        self.anonymous_id = str(uuid.uuid1())

        # Session time is time in EPOC that must be passed to Segment in each track event to ensure that a single
        # session is maintained. The client side CLI should generate this and submit the string with each API submission
        self.session_time = math.floor(time.time())

    def send_track(self, event_name, event_properties, user_id=None):
        track_dict = {
            'anonymous_id': self.anonymous_id,
            'wizard_name': event_name,
            'installation_id': self.device_id,
            'deployment_type': 'BareOS'
        }
        # append event_properties to track_dict as is
        track_dict.update(event_properties)
        track_user_id = self.anonymous_id
        if user_id:
            track_dict['user_id'] = user_id
            track_user_id = user_id
        try:
            analytics.track(track_user_id, event_name, track_dict,
                anonymous_id=self.anonymous_id,
                # The 'integrations array begin passed below is how the 'session' identifier is passed into Amplitude
                integrations={
                    'Amplitude': {
                        'session_id': self.session_time
                    }
                }
            )
        except Exception as except_err:
            logger.error("Exception in send_track while communicating to segment")
            logger.exception(except_err)

    def send_identify(self, email, user_id):
        try:
            analytics.identify(user_id, {
                'anonymous_id': self.anonymous_id,
                'installation_id': self.device_id,
                'email': email,
                'user_id': user_id,
                'deviceId': user_id,
                # all DATE and TIME submissions need to be in ISO 8601 format
                'createdAt': datetime.datetime.now().isoformat(),
                },
               anonymous_id=self.anonymous_id,
            )
            # Associate old unauthenticated events to post-authenticated events
            analytics.alias(self.anonymous_id, user_id)
        except Exception as except_err:
            logger.error("Exception in send_identify while communicating to segment")
            logger.exception(except_err)

    def send_group(self, user_id, du_account_url):
        try:
            analytics.group(user_id, du_account_url, traits={'ddu_url_': 'DU', 'account_url_': du_account_url,
                                                             'cli_last_executed_at': datetime.datetime.now().isoformat()},
                            anonymous_id=self.anonymous_id)
        except Exception as except_err:
            logger.error("Exception in send_group while communicating to segment")
            logger.exception(except_err)
