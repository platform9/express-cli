"""
Exceptions for Core CLI Operations
"""

class CLIException(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __repr__(self):
        return self.msg

class UserAuthFailure(CLIException):
    def __init__(self, msg):
        super(UserAuthFailure, self).__init__(msg)

