"""
Sage Intacct AR Invoice
"""

from .api_base import ApiBase


class ReadReport(ApiBase):
    """Class for AR Invoice APIs."""
    def __init__(self):
        ApiBase.__init__(self, dimension='readReport')
