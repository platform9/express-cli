"""
Exceptions for Cluster Operations
"""

class CLIException(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __repr__(self):
        return self.msg

class ClusterCLIException(CLIException):
    def __init__(self, msg):
        self.msg = msg
        super(ClusterCLIException, self).__init__(msg)

    def __repr__(self):
        return self.msg

class SSHInfoMissing(ClusterCLIException):
    def __init__(self, missing_fields):
        msg = "Missing SSH details. Need following: {}".format(missing_fields)
        super(SSHInfoMissing, self).__init__(msg)

class MissingVIPDetails(ClusterCLIException):
    def __init__(self, missing_fields):
        msg = "VIP details needed for multimaster setups. Missing fields: {}".format(missing_fields)
        super(MissingVIPDetails, self).__init__(msg)

class ClusterCreateFailed(ClusterCLIException):
    def __init__(self, msg):
        super(ClusterCreateFailed, self).__init__(msg)

class ClusterAttachFailed(ClusterCLIException):
    def __init__(self, msg):
        super(ClusterAttachFailed, self).__init__(msg)

class FailedActiveMasters(ClusterCLIException):
    def __init__(self, msg):
        super(FailedActiveMasters, self).__init__(msg)

class PrepNodeFailed(ClusterCLIException):
    def __init__(self, msg):
        super(PrepNodeFailed, self).__init__(msg)

class UserAuthFailure(CLIException):
    def __init__(self, msg):
        super(UserAuthFailure, self).__init__(msg)
