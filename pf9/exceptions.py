"""
Exceptions for Core CLI Operations
"""


class CLIException(Exception):
    def __init__(self, msg):
        super(CLIException, self).__init__(msg)
        self.msg = msg

    def __repr__(self):
        return self.msg


class DUCommFailure(CLIException):
    def __init__(self, msg):
        super(DUCommFailure, self).__init__(msg)


class UserAuthFailure(CLIException):
    def __init__(self, msg):
        super(UserAuthFailure, self).__init__(msg)
